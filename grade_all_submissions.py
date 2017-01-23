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

    netids = os.listdir(submissions_directory)

    count = 0
    fail_count = 0
    plist = {}
    for netid in netids:
        print("Attempting to grade submissions for: %s" % netid)
        args = ["python", "grade_submission.py",
                "-d", submissions_directory,
                "-a", assignment_name,
                "-l", netid,
                "-C", autograder_command]
        # success = subprocess.call(args)
        # if success == 0:
        #     count += 1
        p = subprocess.Popen(args)
        plist[netid] = p

    for netid in plist:
        p = plist[netid]
        p.wait()
        if p.returncode == 0:
            count += 1
        else:
            fail_count +=1

    duration = time.time() - start

    msg = "%d submissions graded" % count
    write_to_log(msg)
    print(msg)

    msg = "%d submissions failed to grade" % fail_count
    write_to_log(msg)
    print(msg)

    msg = "%d seconds elapsed" % duration
    write_to_log(msg)
    print(msg)