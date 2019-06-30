#!/usr/bin/env python3

import argparse
import glob
import os
import re
import shutil
import stat
import subprocess
import yaml

# Copied from:
# https://stackoverflow.com/a/22331852/384888
def copytree(src, dst, symlinks = False, ignore = None):
  if not os.path.exists(dst):
    os.makedirs(dst)
    shutil.copystat(src, dst)
  lst = os.listdir(src)
  if ignore:
    lst = [x for x in lst if x not in ignore]
  for item in lst:
    s = os.path.join(src, item)
    d = os.path.join(dst, item)
    if symlinks and os.path.islink(s):
      if os.path.lexists(d):
        os.remove(d)
      os.symlink(os.readlink(s), d)
      try:
        st = os.lstat(s)
        mode = stat.S_IMODE(st.st_mode)
        os.lchmod(d, mode)
      except:
        pass # lchmod not available
    elif os.path.isdir(s):
      copytree(s, d, symlinks, ignore)
    else:
      shutil.copy2(s, d)

class PerforceChangelist:
    def __init__(self, revision, date, time, submitter):
        self.revision = revision
        self.date = date.replace("/", "-")
        self.time = time
        self.submitter = submitter
        self.description_lines = []

    def __str__(self):
        return self.revision + " " + self.date + " " + self.time + " " + self.submitter

    def set_description(self, description_lines):
        self.description_lines = description_lines

def git(*args):
    completed_process = subprocess.run(['git'] + list(args), stdout=subprocess.PIPE, check=True)
    return completed_process

def p4(*args):
    completed_process = subprocess.run(['p4.exe'] + list(args), stdout=subprocess.PIPE, check=True)
    return completed_process

def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--outputPath", type=str, help="")
    parser.add_argument("--workspacePath", type=str, help="")
    parser.add_argument("--p4workspace", type=str, help="")
    parser.add_argument("--p4depotpath", type=str, help="")
    args = parser.parse_args()

    if not args.outputPath:
        print("ERROR:", "outputPath not supplied")
        return

    if not args.workspacePath:
        print("ERROR:", "workspacePath not supplied")
        return

    if not args.p4workspace:
        print("ERROR:", "p4workspace not supplied")
        return

    if not args.p4depotpath:
        print("ERROR:", "p4depotpath not supplied")
        return

    try:
        with open("settings.yaml", 'r') as stream:
            try:
                settings = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print("ERROR:", exc)
                return
    except Exception as e:
        print("ERROR:", e)
        return

    if not settings["usermapping"]:
        print("ERROR:", "'usermapping' key not found in settings.yaml")
        return

    print("Creating '" + args.outputPath + "'")

    try:
        os.mkdir(args.outputPath)
    except OSError as e:
        print("ERROR:", e)
        return

    try:
        completed_process = git("-C", args.outputPath, "init")
    except subprocess.CalledProcessError as e:
        print("ERROR:", e)
        return

    try:
        completed_process = p4("changes", "-t", "-s", "submitted", args.p4depotpath)
    except subprocess.CalledProcessError as e:
        print("ERROR:", e)
        return

    output_str = completed_process.stdout.decode("utf-8").strip()
    lines = output_str.split("\n")

    changelists = []
    for line in lines:
        match = re.search(r"Change (\d+) on (\S+) (\S+) by (\w+)@\S+ '.*", line)
        cl = PerforceChangelist(match.groups()[0], match.groups()[1], match.groups()[2], match.groups()[3])
        changelists.append(cl)

        if cl.submitter not in settings["usermapping"]:
            print("ERROR:", "Missing name in the look up table:", cl.submitter)
            return

    changelists.reverse()

    for cl in changelists:
        print(cl)
        try:
            completed_process = p4("changes", "-l", "@=" + cl.revision)
        except subprocess.CalledProcessError as e:
            print("ERROR:", e)
            return

        output_str = completed_process.stdout.decode("utf-8").strip()
        lines = output_str.split("\n")
        cl.set_description([line.strip() for line in lines[2:]])

        for line in cl.description_lines:
           print(line)

        try:
            completed_process = p4("-c", args.p4workspace, "sync", "-f", args.p4depotpath + "@" + cl.revision + ",@" + cl.revision)
        except subprocess.CalledProcessError as e:
            print("ERROR:", e)
            return

        try:
            copytree(args.workspacePath, args.outputPath, ignore=[".gitignore"])
        except Exception as e:
            print("ERROR:", e)
            return

        try:
            completed_process = git("-C", args.outputPath, "add", "-A")
        except subprocess.CalledProcessError as e:
            print("ERROR:", e)
            return

        try:
            author = settings["usermapping"][cl.submitter]
            author_name_email = author["name"] + " <" + author["email"] + ">"
            os.environ["GIT_COMMITTER_NAME"] = author["name"]
            os.environ["GIT_COMMITTER_EMAIL"] = author["email"]

            date = cl.date + "T" + cl.time
            os.environ["GIT_COMMITTER_DATE"] = date

            message = "\n".join(cl.description_lines)

            completed_process = git("-C", args.outputPath, "commit", "-m", message, "--date", date, "--author=" + author_name_email)
        except subprocess.CalledProcessError as e:
            print("ERROR:", e)
            return

        # We just remove everything so that we're always getting an accurate conversion of each p4 changelist, including deleted/renamed files.
        # There's obviously better ways of doing this but our repo is small enough that this is quick and easy.
        if cl.revision != changelists[-1].revision:
            for f in glob.glob(args.outputPath + "/*"):
                if os.path.isdir(f):
                    if f != ".git":
                        shutil.rmtree(f)
                else:
                    os.remove(f)

if __name__ == "__main__":
    main()
