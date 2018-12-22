# rl-p4-to-git

This is a simple script to perform a one way conversion from perforce to git while preserving author information, commit date, and log messages. It does not require admin access to the perforce repo.

This was designed to be used on a p4 depot less than 10MB which has less than 500 commits.

You can extract a git repo from a sub-directory of the perforce depot. Thus if you have the following:

- `//Depot/Main/ProjectA`
- `//Depot/Main/ProjectB`

You can create a git repo consisting of just commits to either `ProjectA` or `ProjectB`.

## Exmple usage:

You must create a `settings.yaml` file with the following format:

```
usermapping:
  rlabrecque:
    name: "Riley Labrecque"
    email: "rlabrecque@redacted.com"
  BuildUser:
    name: "Build User"
    email: "build@redacted.com"
```

`./rl-p4-to-git.py --outputPath output --p4workspace rlabrecque_Redacted_Main --p4depotpath //Redacted/Main/some/repo/... --workspacePath /mnt/f/Redacted/some/repo`
