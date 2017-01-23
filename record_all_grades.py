from optparse import OptionParser
import os
import json
from utils import get_assignment_name_and_id, write_to_log, write_header_row
import subprocess
import csv
import copy
import sys
import time


parser = OptionParser(usage="Usage: %prog [options]",
                      description="Record all grades in csv.  Optionally, upload results to canvas.                "
                                  "For example, try:                                                             "
                                  "python " + __file__ + " -d <submissions-directory> -a <assignment_name> "
                                                         "-U True")
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
parser.add_option("-U", "--upload-results",
                  dest="upload_results", default="False", type=str,
                  help="If True, uploads comment attachment to Canvas containing autograder_results.  Also uploads score.")
parser.add_option("-c", "--course-id",
                  dest="course_id", default=None, type=int,
                  help="The Canvas course_id.  e.g. 43589.  Only required when uploading results.")


if __name__ == "__main__":
    start = time.time()

    (options, args) = parser.parse_args()

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

    course_id = options.course_id

    upload_results = options.upload_results
    if upload_results.lower() == "false":
        upload_results = False
    elif upload_results.lower() == "true":
        upload_results = True
        assert isinstance(course_id, int), "course_id must be a valid int when uploading results: %s" % course_id
    else:
        print("upload_results must be 'true' or 'false': %s" % upload_results)
        sys.exit(1)

    netids = os.listdir(submissions_directory)

    count = 0
    fail_count = 0
    grades = []
    for netid in netids:
        assignment_directory = os.path.join(submissions_directory, netid, assignment_name)

        if not os.path.isdir(assignment_directory):
            msg = "%s: %s is not a directory.  Skipping." % (__file__, assignment_directory)
            write_to_log(msg)
            print(msg)
            continue

        autograder_results = os.path.join(assignment_directory, "autograder_results.txt")
        if not os.path.isfile(autograder_results):
            msg = "%s: %s is not a file.  Skipping." % (__file__, autograder_results)
            write_to_log(msg)
            print(msg)
            continue

        with open(autograder_results, "r") as f:
            lines = f.readlines()

        last_line = lines[-1]

        try:
            summary = json.loads(last_line)
        except ValueError as E:
            msg = "%s: Unable to load summary [%s]" % (__file__, E)
            write_to_log(msg)
            print(msg)
            continue
        else:
            assert isinstance(summary, dict)

        team_netids = summary["team_login_ids"]
        points_received = summary["points_received"]
        points_possible = summary["points_possible"]
        percent = float(points_received) / float(points_possible) * 100
        percent_as_string = "{0:0.1f}%".format(percent)

        summary["percent_as_string"] = percent_as_string
        summary["student"] = ""

        # inner loop to handle each individual student
        for student in team_netids:
            summary.update({"student": student})
            grades.append(copy.deepcopy(summary))

            if upload_results == True:
                args = ["python", "upload_result_comment.py",
                        "-c", str(course_id),
                        "-f", autograder_results,
                        "-g", percent_as_string,
                        "-a", assignment_name,
                        "-l", student]
                return_code = subprocess.call(args)

                if return_code == 0:
                    count += 1
                else:
                    fail_count += 1

    grades_csv = os.path.join(submissions_directory, "..", assignment_name + "_grades.csv")
    with open(grades_csv, "w") as f:
        fieldnames = grades[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        write_header_row(writer, fieldnames)

        for item in grades:
            writer.writerow(item)

    duration = time.time() - start

    msg = "%d grades uploaded successfully" % count
    write_to_log(msg)
    print(msg)

    msg = "%d grades failed to upload" % fail_count
    write_to_log(msg)
    print(msg)

    msg = "%d seconds elapsed" % duration
    write_to_log(msg)
    print(msg)