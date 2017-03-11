from optparse import OptionParser
import os
from utils import get_assignment_name_and_id, get_netid_and_user_id, write_to_log, convert_Z_to_UTC
import shutil
import subprocess
import json
import sys
import datetime

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
parser.add_option("-m",
                  dest="make_assignment_directory", action="store_true", default=False,
                  help="If the assignment directory doesn't exist, should it be created?")
parser.add_option("-f",
                  dest="force_do_grading", action="store_true", default=False,
                  help="Do grading even if submission appears to already have been graded.")
parser.add_option("-c", "--course-id",
                  dest="course_id", default=None, type=int,
                  help="The Canvas course_id.  e.g. 43589.")
parser.add_option("-C", "--autograder-command",
                  dest="autograder_command", default=None, type=str,
                  help="A command which, when run from within the student's assignment subdirectory, would "
                       "automatically grade the student's submission, printing the results to stdout.  The last line of "
                       "the output must be in JSON format with the following fields:                          "
                       "{'points_possible': <int>, "
                       "'points_received': <int>, "
                       "'team_login_ids': [login_id_1, login_id_2, ...]}"
                       "It may optionally contain the field 'submitter_login_id': <login_id>")

RETURNCODE_SUCCESS = 0
RETURNCODE_NO_SUBMISSION = 1
RETURNCODE_OTHER = 2
RETURNCODE_ALREADY_GRADED = 3
RETURNCODE_FAILED = 4


def update_autograder_history_file(autograder_history_file, autograder_summary):
    '''
    Add this autograder_summary to the list of summaries in the history file
    :param autograder_history_file: filename of a json file containing a list of autograder summaries
    :param autograder_summary: a dictionary containing this autograder summary
    :return: None
    '''
    assert isinstance(autograder_summary, dict)

    if os.path.isfile(autograder_history_file):
        with open(autograder_history_file, "r") as f:
            autograder_history = json.load(f)
    else:
        autograder_history = []

    assert isinstance(autograder_history, list)

    autograder_history.append(autograder_summary)

    with open(autograder_history_file, "w") as f:
        json.dump(autograder_history, f)


def get_submitted_at(submission_summary_file):
    assert os.path.isfile(submission_summary_file), "not a valid file: %s" % submission_summary_file

    with open(submission_summary_file, "r") as f:
        summary = json.load(f)

    return summary["submitted_at"]


def should_do_grading(submission_summary_file, results_file):
    if not os.path.isfile(submission_summary_file):
        # if there is no submission summary, must do grading
        return True, None, None

    if not os.path.isfile(results_file):
        # if there is no existing autograder result, must do grading
        return True, None, None

    # get Canvas time of submission
    submitted_at = get_submitted_at(submission_summary_file)

    # get Canvas time of the file that was graded
    with open(results_file, "r") as f:
        # get graded version (if any)
        lines = f.readlines()
        try:
            summary = json.loads(lines[-1])
        except (ValueError, IndexError) as E:
            # if we can't read the autograder summary, must do grading
            return True, None, None

    if "graded_version" not in summary.keys():
        # if there is no info about the graded version, must do grading
        return True, None, None

    graded_version = summary["graded_version"]

    if graded_version == "N/A":
        return True, None, None

    submitted_at = convert_Z_to_UTC(str(submitted_at))
    submitted_at_time = datetime.datetime.strptime(submitted_at, "%Y-%m-%dT%H:%M:%S%Z").timetuple()
    graded_version = convert_Z_to_UTC(str(graded_version))
    graded_version_time = datetime.datetime.strptime(graded_version, "%Y-%m-%dT%H:%M:%S%Z").timetuple()

    if graded_version_time >= submitted_at_time:
        # if graded version time is later or same as submitted version time, we've already graded it
        return False, graded_version, submitted_at
    else:
        return True, graded_version, submitted_at


if __name__ == "__main__":
    (options, args) = parser.parse_args()

    autograder_command = options.autograder_command
    assert isinstance(autograder_command, str), "autograder_command is invalid or not provided: %s" % autograder_command

    submissions_directory = options.submissions_directory
    assert isinstance(submissions_directory, str), "submissions_directory not provided? [%s]" % submissions_directory
    assert os.path.isdir(
        submissions_directory), "submissions_directory is not a valid directory: %s" % submissions_directory

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

    roster_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                       "resources",
                                       "roster.csv")
    assert os.path.isfile(roster_file), "roster_file is not a valid file: %s" % roster_file

    assignment_list = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                       "resources",
                                       "assignments.csv")
    assert os.path.isfile(assignment_list), "assignment_list is not a valid file: %s" % assignment_list

    course_id = options.course_id  # this arg is optional

    assignment_name, assignment_id = get_assignment_name_and_id(assignment_name, assignment_id, assignment_list,
                                                                course_id)

    try:
        login_id, user_id = get_netid_and_user_id(login_id, user_id, roster_file)
    except:
        msg = "%s: unable to find student in roster.  netid [%s] user_id [%s].  Dropped class?.  Exiting." % \
              (__file__, str(login_id), str(user_id))
        print(msg)
        write_to_log(msg)
        sys.exit(RETURNCODE_OTHER)

    assignment_directory = os.path.join(submissions_directory, login_id, assignment_name)

    make_assignment_directory = options.make_assignment_directory
    assert isinstance(make_assignment_directory,
                      bool), "-m flag did not give valid bool: %s" % make_assignment_directory

    force_do_grading = options.force_do_grading
    assert isinstance(force_do_grading,
                      bool), "-f flag did not give valid bool: %s" % force_do_grading

    if not os.path.isdir(assignment_directory):
        msg = "%s: Directory does not exist: %s" % (__file__, assignment_directory)

        if not make_assignment_directory:
            msg += ". Exiting.  (If you wish to automatically create the necessary directories, re-run " \
                   "with the '-m true' option."
            print(msg)
            write_to_log(msg)
            sys.exit(RETURNCODE_NO_SUBMISSION)
        else:
            msg += ". Creating directory."
            print(msg)
            write_to_log(msg)
            os.mkdir(assignment_directory, 0755)

    # make a temporary directory in the submissions directory (to be safe, make it the same depth as actual assignment
    # subdirectory
    temp_directory = os.path.join(submissions_directory, login_id + "_tmp")
    if os.path.isdir(temp_directory):
        msg = "%s: Directory [%s] already exists.  Exiting with code [%d]" % (
        __file__, temp_directory, RETURNCODE_FAILED)
    os.mkdir(temp_directory, 0755)

    # copy the student's submission to the temporary directory
    destination_directory = os.path.join(temp_directory, assignment_name)
    shutil.copytree(src=assignment_directory, dst=destination_directory)

    # change directory into the temporary directory
    os.chdir(destination_directory)

    # check if this submission has already been graded
    submission_summary_file = "submission.json"
    results_file = "autograder_results.txt"
    do_grading, graded_version, submitted_at = should_do_grading(submission_summary_file, results_file)

    if do_grading or force_do_grading:
        # run the autograder command, piping output to autograder_results.txt
        with open(results_file, "w") as f:
            args = autograder_command.split(" ")

            # change '~' to $HOME
            HOME = os.environ["HOME"]
            for i in range(0, len(args)):
                if args[i].startswith('~'):
                    args[i] = args[i].replace('~', HOME, 1)

            if force_do_grading and "-f" not in args:
                args.append("-f")

            returncode = subprocess.call(args, stdout=f, stderr=subprocess.STDOUT)

        if returncode != 0:
            msg = "%s: command failed [%s] with exit code [%d] for student [%s].  Exiting." % (
                __file__, " ".join(args), returncode, login_id)
            write_to_log(msg)
            print(msg)
            shutil.copy2(results_file, assignment_directory)
            shutil.rmtree(temp_directory, ignore_errors=True)
            sys.exit(returncode)

    else:
        msg = "%s: for student [%s], this submission [%s] was previously graded at [%s].  Exiting." % (
            __file__, login_id, submitted_at, graded_version)
        write_to_log(msg)
        print(msg)
        shutil.rmtree(temp_directory)
        sys.exit(RETURNCODE_ALREADY_GRADED)

    # process autograder json summary
    lines = open(results_file, "r").readlines()
    try:
        autograder_summary = json.loads(lines[-1])
    except ValueError as E:
        msg = "%s: for student [%s], error [%s]" % (__file__, login_id, E)
        write_to_log(msg)
        print(msg)
        shutil.copy2(results_file, assignment_directory)
        shutil.rmtree(temp_directory)
        sys.exit(RETURNCODE_OTHER)

    if "submitter_login_id" in autograder_summary.keys():
        # if submitter_login_id is already there, make sure it doesn't end in "_tmp"
        submitter_login_id = str(autograder_summary["submitter_login_id"])
        if submitter_login_id.endswith("_tmp"):
            submitter_login_id = submitter_login_id[:-4]
            autograder_summary["submitter_login_id"] = submitter_login_id
    else:
        # otherwise, use the command line option login_id as the submitter
        autograder_summary["submitter_login_id"] = login_id

    # record which submission was graded
    submitted_at = get_submitted_at(submission_summary_file)
    autograder_summary["graded_version"] = submitted_at

    clean_netids = []
    dirty_netids = autograder_summary["team_login_ids"]
    for netid in dirty_netids:
        if netid.endswith("_tmp"):
            netid = netid[:-4]
        clean_netids.append(netid)

    autograder_summary["team_login_ids"] = clean_netids

    lines[-1] = json.dumps(autograder_summary)
    open(results_file, "w").writelines(lines)

    # print summary
    print("Summary:")
    print(lines[-1])

    # copy autograder_results.txt to the student's assignment subdirectory
    shutil.copy2(results_file, assignment_directory)
    shutil.copy2(submission_summary_file, assignment_directory)

    # update autograder_history file and copy to student's subdirectory
    autograder_history_file = "autograder_history.json"
    update_autograder_history_file(autograder_history_file, autograder_summary)
    shutil.copy2(autograder_history_file, assignment_directory)

    # delete the temporary directory and exit
    shutil.rmtree(temp_directory)
    sys.exit(RETURNCODE_SUCCESS)
