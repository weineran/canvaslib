from optparse import OptionParser
import os
from utils import get_assignment_name_and_id, write_to_log
import subprocess
import time


parser = OptionParser(usage="Usage: %prog [options]",
                      description="Grade all submissions in the submissions directory.  Not all arguments are required.                "
                                  "For example, try:                                                             "
                                  "python " + __file__ + " -d <submissions-directory> -a <assignment_name> "
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
parser.add_option("-L", "--assignment_list",
                  dest="assignment_list",
                  default=os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                       "resources",
                                       "assignments.csv"),
                  type=str,
                  help="The path to a .csv file containing a list of assignments.  At a minimum, should have columns labeled "
                       "'assignment_name' and 'assignment_id'.")
parser.add_option("-m",
                  dest="make_assignment_directory", action="store_true", default=False,
                  help="If the assignment directory doesn't exist, should it be created?")
parser.add_option("-f",
                  dest="force_do_grading", action="store_true", default=False,
                  help="Do grading even if submission appears to already have been graded.")
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


if __name__ == "__main__":
    start = time.time()

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

    assignment_list = options.assignment_list
    assert os.path.isfile(assignment_list), "assignment_list is not a valid file: %s" % assignment_list

    assignment_name, assignment_id = get_assignment_name_and_id(assignment_name, assignment_id, assignment_list)

    make_assignment_directory = options.make_assignment_directory
    assert isinstance(make_assignment_directory, bool), "-m flag gave invalid value: %s" % make_assignment_directory

    force_do_grading = options.force_do_grading
    assert isinstance(force_do_grading, bool), "-f flag gave invalid value: %s" % force_do_grading

    netids = os.listdir(submissions_directory)

    count = 0
    no_submission_count = 0
    other_list = []
    already_graded = 0
    fail_list = []
    unknown_list = []
    plist = {}
    for netid in netids:
        print("Attempting to grade submissions for: %s" % netid)
        arguments = ["python", "grade_submission.py",
                "-d", submissions_directory,
                "-a", assignment_name,
                "-l", netid,
                "-C", autograder_command]

        if make_assignment_directory:
            arguments.append("-m")

        if force_do_grading:
            arguments.append("-f")

        p = subprocess.Popen(arguments)
        plist[netid] = p

    for netid in plist:
        p = plist[netid]
        p.wait()
        return_code = p.returncode
        
        if return_code == RETURNCODE_SUCCESS:
            count += 1
        elif return_code == RETURNCODE_NO_SUBMISSION:
            no_submission_count += 1
        elif return_code == RETURNCODE_OTHER:
            other_list.append(netid)
        elif return_code == RETURNCODE_ALREADY_GRADED:
            already_graded += 1
        elif return_code == RETURNCODE_FAILED:
            fail_list.append(netid)
        else:
            unknown_list.append(netid)

    duration = time.time() - start

    msg = "%d submissions graded" % count
    write_to_log(msg)
    print(msg)

    msg = "%d directories skipped (no submission)" % no_submission_count
    write_to_log(msg)
    print(msg)

    msg = "%d submissions skipped (previously graded)" % already_graded
    write_to_log(msg)
    print(msg)

    msg = "%d submissions failed to grade: %s" % (len(fail_list), fail_list)
    write_to_log(msg)
    print(msg)

    msg = "%d submissions had other problem: %s" % (len(other_list), other_list)
    write_to_log(msg)
    print(msg)

    if len(unknown_list) > 0:
        msg = "%d submissions had UNKNOWN problem: %s" % (len(unknown_list), unknown_list)
        write_to_log(msg)
        print(msg)

    msg = "%d seconds elapsed" % duration
    write_to_log(msg)
    print(msg)