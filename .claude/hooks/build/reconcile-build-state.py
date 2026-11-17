#!/usr/bin/env python3
"""reconcile-build-state.py — ancla el estado a la realidad (git + tests). Fail-open.

Deriva/reconcilia, nunca lanza:
- wiring_checklist: un item 'passing' sin 'evidence' se degrada a 'failing' (self-heal).
- branch_drift: si la rama git real != active_slice.branch, lo anota (no corrige).
- ratchet: no revierte gates booleanos true->false (solo señal explícita lo haría).
Uso: reconcile-build-state.py [<state-file>]
"""
import json, os, sys, subprocess, tempfile

def git_branch(root):
    try:
        return subprocess.run(["git","-C",root,"rev-parse","--abbrev-ref","HEAD"],
                              capture_output=True,text=True,timeout=5).stdout.strip() or None
    except Exception:
        return None

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.environ.get("CLAUDE_PROJECT_DIR",os.getcwd()), ".claude","state","build-state.json")
    try:
        with open(path) as fh:
            d = json.load(fh)
    except Exception:
        return 0  # fail-open
    if not isinstance(d, dict):
        return 0
    changed = False
    s = d.get("active_slice")
    if isinstance(s, dict):
        try:
            # 1) wiring: passing sin evidencia -> failing
            wc = s.get("wiring_checklist")
            wc = wc if isinstance(wc, list) else []
            for w in wc:
                if not isinstance(w, dict):
                    continue
                if w.get("status") == "passing" and not (w.get("evidence") or "").strip():
                    w["status"] = "failing"; changed = True
            # 2) branch drift
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(path))))
            rb = git_branch(root)
            if rb and s.get("branch") and rb != s["branch"] and rb not in ("HEAD",):
                if s.get("branch_drift") != rb:
                    s["branch_drift"] = rb; changed = True
            elif s.get("branch_drift") and rb == s.get("branch"):
                s.pop("branch_drift", None); changed = True
        except Exception:
            pass
    if changed:
        try:
            dirn = os.path.dirname(path) or "."
            fd, tmp = tempfile.mkstemp(dir=dirn, prefix=".build-state.", suffix=".tmp")
        except Exception:
            return 0
        try:
            with os.fdopen(fd,"w") as o:
                json.dump(d,o,indent=2,ensure_ascii=False); o.flush(); os.fsync(o.fileno())
            os.replace(tmp, path)
            sys.stderr.write("reconcile: estado re-anclado a disco\n")
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
