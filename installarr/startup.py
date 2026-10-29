"""Container-side startup gate, evaluated again on every Docker restart.

Host checks alone leave a race before the daemon binds the source. This gate
checks what the container actually received before executing its entrypoint.
Use private bind propagation so a running container retains that mount view.
"""
from pathlib import PurePosixPath
import shlex

from .storage import validate_checks


def container_mount_assertion(host_path, target, expected):
    validate_checks({"mount": expected}, ["mount"])
    if "sentinel" not in expected:
        raise ValueError("Startup protection requires a reachable sentinel")
    path, mountpoint = PurePosixPath(host_path), PurePosixPath(expected["mountpoint"])
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("Invalid host storage path")
    try:
        relative = path.relative_to(mountpoint)
    except ValueError:
        raise ValueError("Storage path is outside asserted mountpoint") from None
    return {"target": target, "source": expected["source"], "fstype": expected["fstype"],
            "sentinel": expected["sentinel"], "root": "/" if str(relative) == "." else "/" + str(relative)}


def render_storage_guard(mounts, require_writable=True):
    if not isinstance(mounts, list) or not mounts:
        raise ValueError("Guard requires explicit storage mount assertions")
    lines = ["#!/bin/sh", "set -eu", "deny() { echo 'Installarr storage startup check failed' >&2; exit 78; }"]
    targets = set()
    for mount in mounts:
        if not isinstance(mount, dict) or set(mount) - {"target", "source", "fstype", "sentinel", "root", "probe"} or not {"target", "source", "fstype", "sentinel"} <= set(mount):
            raise ValueError("Invalid container storage assertion")
        mount = dict(mount, root=mount.get("root", "/"))
        root = mount["root"]
        if not isinstance(root, str) or not root.startswith("/") or ".." in PurePosixPath(root).parts:
            raise ValueError("Invalid mount subtree root")
        target = mount["target"]
        probe = mount.get("probe", target)
        if not isinstance(probe, str) or ".." in PurePosixPath(probe).parts:
            raise ValueError("Invalid guard probe path")
        try:
            relative_probe = PurePosixPath(probe).relative_to(PurePosixPath(target))
        except ValueError:
            raise ValueError("Guard probe must stay inside its data mount") from None
        if (not isinstance(target, str) or not target.startswith("/") or target == "/"
                or ".." in PurePosixPath(target).parts or (target, probe) in targets):
            raise ValueError("Invalid or duplicate container mount target")
        targets.add((target, probe))
        validate_checks({"mount": {"mountpoint": target, **{key: mount[key] for key in ("source", "fstype", "sentinel")}}}, ["mount"])
        # /proc mountinfo escapes whitespace/backslashes. Refuse ambiguity rather
        # than accepting a differently decoded source/target. Sentinel is a basename.
        if any(not value or any(c.isspace() or c in "\\\x00" for c in value) for value in mount.values()):
            raise ValueError("Ambiguous mountinfo fields")
        if "/" in mount["sentinel"] or mount["sentinel"] in (".", ".."):
            raise ValueError("Guard sentinel must be a single filename")
        for key in ("target", "source", "fstype", "sentinel"):
            lines.append("{}={}".format(key, shlex.quote(mount[key])))
        lines.append("expected_root={}".format(shlex.quote(root)))
        # Linux can show an NFS subtree either as export + mount-root, or as
        # export/subtree + root '/'. Accept only those two exact identity pairs.
        lines.append("subtree_source={}".format(shlex.quote(mount["source"].rstrip("/") + (root if root != "/" else ""))))
        lines.extend([
            "matched=no",
            "target_count=0",
            "matched_options=",
            "matched_mid=",
            "while IFS=' ' read -r mid parent dev root actual options rest; do",
            '  [ "$actual" = "$target" ] || continue',
            '  target_count=$((target_count + 1))',
            '  case " $rest " in *" - $fstype $source ro"*|*" - $fstype $subtree_source ro"*) deny ;; esac',
            '  if [ "$root" = "$expected_root" ]; then',
            '    case " $rest " in *" - $fstype $source "*) matched=yes; matched_options=$options; matched_mid=$mid ;; esac',
            '  fi',
            '  if [ "$root" = / ]; then',
            '    case "$fstype" in nfs|nfs4|cifs)',
            '      case " $rest " in *" - $fstype $subtree_source "*) matched=yes; matched_options=$options; matched_mid=$mid ;; esac ;;',
            '    esac',
            '  fi',
            "done < /proc/self/mountinfo",
            '[ "$target_count" = 1 ] && [ "$matched" = yes ] || deny',
            'case ",$matched_options," in *,ro,*) deny ;; esac',
        ])
        lines.append('probe="$target"')
        for component in relative_probe.parts:
            if component != '.':
                lines.append('probe="$probe"/' + shlex.quote(component))
                lines.append('[ ! -L "$probe" ] && [ -d "$probe" ] || deny')
        lines.extend([
            'exec 3< "$probe" || deny',
            'probe_mid=',
            'while read -r key value rest; do [ "$key" != mnt_id: ] || probe_mid=$value; done < /proc/self/fdinfo/3',
            '[ "$probe_mid" = "$matched_mid" ] || deny',
            '[ ! -L "$probe/$sentinel" ] && [ -f "$probe/$sentinel" ] && [ -r "$probe/$sentinel" ] || deny',
            'IFS= read -r health < "$probe/$sentinel" || deny',
            'exec 3<&-',
        ])
    if not require_writable:
        lines = [line for line in lines if line not in (
            '  case " $rest " in *" - $fstype $source ro"*|*" - $fstype $subtree_source ro"*) deny ;; esac',
            'case ",$matched_options," in *,ro,*) deny ;; esac')]
    lines.extend(['[ "$#" -gt 0 ] || deny', 'exec "$@"', ""])
    return "\n".join(lines)
