from optparse import OptionParser
import os
from utils import get_assignment_name_and_id, get_netid_and_user_id, write_to_log
import shutil
import subprocess
import json
import sys


parser = OptionParser(usage="Usage: %prog [options]",
                      description="Grade a single submission.  Not all arguments are required.                "
                                  "For example, try:                                                             "
                                  "python " + __file__ + " -d <submissions-directory> -a <assignment_name> -l <login_id> "
                                                         "-C 'python <your-autograder-script>'")
parser.add_option("-d", "--submissions-directory",
                  dest="submissions_directory", default=None, type=str,
                  help="The path to the submissions directory.  The submissions directory contains subdirectories for "
                       "each student.  Each student subdirectory contains subdirectories for each assignment.")
parser.add_option("-a", "--assignment-name",
                  dest="assignment_name", default=None, type=str,
                  help="The name of the assignment to download.  e.g. 'proj4'")
parser.add_option("-i", "--assignment-id",
                  dest="assignment_id", default=None, type=int,
                  help="The Canvas assignment_id of the assignment to download.")
parser.add_option("-u", "--user-id",
                  dest="user_id", default=None, type=int,
                  help="The Canvas user_id of the student whose assignment you wish to grade.")
parser.add_option("-l", "--login-id",
                  dest="login_id", default=None, type=str,
                  help="The Canvas login_id (netid) of the student whose assignment you wish to grade.")
parser.add_option("-r", "--roster",
                  dest="roster",
                  default=os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                       "resources",
                                       "roster.csv"),
                  type=str,
                  help="The path to a .csv file containing a class roster.  At a minimum, should have columns labeled "
                       "'login_id' (e.g. awp066) and 'id' (the Canvas user_id).")
parser.add_option("-L", "--assignment_list",
                  dest="assignment_list",
                  default=os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                       "resources",
                                       "assignments.csv"),
                  type=str,
                  help="The path to a .csv file containing a list of assignments.  At a minimum, should have columns labeled "
                       "'assignment_name' and 'assignment_id'.")
parser.add_option("-C", "--autograder-command",
                  dest="autograder_command", default=None, type=str,
                  help="A command which, when run from within the student's assignment subdirectory, would "
                       "automatically grade the student's submission, printing the results to stdout.  The last line of "
                       "the output must be in JSON format with the following fields:                          "
                       "{'points_possible': <int>, "
                       "'points_received': <int>, "
                       "'team_login_ids': [login_id_1, login_id_2, ...]}"
                       "It may optionally contain the field 'submitter_login_id': <login_id>")


if __name__ == "__main__":
    (options, args) = parser.parse_args()

    autograder_command = options.autograder_command
    assert isinstance(autograder_command, str), "autograder_command is invalid or not provided: %s" % autograder_command

    submissions_directory = options.submissions_directory
    assert isinstance(submissions_directory, str), "submissions_directory not provided? [%s]" % submissions_directory
    assert os.path.isdir(submissions_directory), "submissions_directory is not a valid directory: %s" % submissions_directory

    assignment_name = options.assignment_name
    assignment_id = options.assignment_id
    assert isinstance(assignment_name, str) or isinstance(assignment_id, int), \
            "A valid assignment_name or assignment_id must be provided.\n" \
            "assignment_name: [%s]\n" \
            "assignment_id: [%s]" % (assignment_name, assignment_id)

    user_id = options.user_id
    login_id = options.login_id
    assert isinstance(login_id, str) or isinstance(user_id, int), \
        "A valid login_id or user_id must be provided.\n" \
        "login_id: [%s]\n" \
        "user_id: [%s]" % (login_id, user_id)

    roster_file = options.roster
    assert os.path.isfile(roster_file), "roster_file is not a valid file: %s" % roster_file

    assignment_list = options.assignment_list
    assert os.path.isfile(assignment_list), "assignment_list is not a valid file: %s" % assignment_list

    assignment_name, assignment_id = get_assignment_name_and_id(assignment_name, assignment_id, assignment_list)
    login_id, user_id = get_netid_and_user_id(login_id, user_id, roster_file)

    assignment_directory = os.path.join(submissions_directory, login_id, assignment_name)

    if not os.path.isdir(assignment_directory):
        print("Directory does not exist: %s" % assignment_directory)
        sys.exit(1)

    # make a temporary directory in the submissions directory (to be safe, make it the same depth as actual assignment
    # subdirectory
    temp_directory = os.path.join(submissions_directory, login_id + "_tmp")
    os.mkdir(temp_directory, 0755)

    # copy the student's submission to the temporary directory
    destination_directory = os.path.join(temp_directory, assignment_name)
    shutil.copytree(src=assignment_directory, dst=destination_directory)

    # change directory into the temporary directory
    os.chdir(destination_directory)

    # run the autograder command, piping output to autograder_results.txt
    results_file = "autograder_results.txt"
    with open(results_file, "w") as f:
        args = autograder_command.split(" ")
        subprocess.call(args, stdout=f, stderr=subprocess.STDOUT)

    # process json summary and print it out
    lines = open(results_file, "r").readlines()
    try:
        summary  = json.loads(lines[-1])
    except ValueError as E:
        msg = "%s: for student [%s], error [%s]" % (__file__, login_id, E)
        write_to_log(msg)
        print(msg)
        shutil.rmtree(temp_directory)
        sys.exit(2)


    if "submitter_login_id" in summary.keys():
        submitter_login_id = str(summary["submitter_login_id"])
        if submitter_login_id.endswith("_tmp"):
            submitter_login_id = submitter_login_id[:-4]
            summary["submitter_login_id"] = submitter_login_id
    else:
        summary["submitter_login_id"] = login_id

    clean_netids = []
    dirty_netids = summary["team_login_ids"]
    for netid in dirty_netids:
        if netid.endswith("_tmp"):
            netid = netid[:-4]
        clean_netids.append(netid)

    summary["team_login_ids"] = clean_netids

    lines[-1] = json.dumps(summary)
    open(results_file,"w").writelines(lines)
    print("Summary:")
    print(lines[-1])

    # copy autograder_results.txt to the student's assignment subdirectory
    shutil.copy2(results_file, assignment_directory)

    # delete the temporary directory
    shutil.rmtree(temp_directory)

