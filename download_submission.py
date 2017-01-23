from optparse import OptionParser
import urllib2
import json
import os
import sys
import datetime
from utils import get_assignment_name_and_id, get_netid_and_user_id, build_canvas_url, open_canvas_page_as_string, \
                  get_token, write_to_log


parser = OptionParser(usage="Usage: %prog [options]",
                      description="Download a single submission.  Not all arguments are required.                "
                                  "For example, try:                                                             "
                                  "python " + __file__ + " -c <course_id> -a <assignment_name> -u <user_id>")
parser.add_option("-c", "--course-id",
                  dest="course_id", default=None, type=int,
                  help="The Canvas course_id.  e.g. 43589")
parser.add_option("-a", "--assignment-name",
                  dest="assignment_name", default=None,
                  help="The name of the assignment to download.  e.g. 'proj4'")
parser.add_option("-i", "--assignment-id",
                  dest="assignment_id", default=None, type=int,
                  help="The Canvas assignment_id of the assignment to download.")
parser.add_option("-d", "--download-directory",
                  dest="download_directory", default=os.getcwd(),
                  help="The path to download the submission to.")
parser.add_option("-o", "--download-filename",
                  dest="download_filename", default=None, type=str,
                  help="The name to give the downloaded file.  If omitted, the name of the student's uploaded file "
                       "will be used.")
parser.add_option("-n", "--netid",
                  dest="netid", default=None,
                  help="The netid of the student whose assignment you wish to download.")
parser.add_option("-u", "--user-id",
                  dest="user_id", default=None, type=int,
                  help="The Canvas user_id of the student whose assignment you wish to download.")
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
parser.add_option("-t", "--token-json-file",
                  dest="token_json_file", default=os.path.join("resources","token.json"), type=str,
                  help="The path to a .json file containing the Canvas authorization token.")


def get_filename(assignment_name, netid):
    # TODO remove this function?
    assert isinstance(assignment_name, str)
    if not isinstance(netid, str):
        netid = ""

    return "xv6_" + assignment_name.replace(" ", "_") + "_" + netid + ".tar.gz"


if __name__ == "__main__":
    (options, args) = parser.parse_args()

    # for token generation, see https://canvas.instructure.com/doc/api/file.oauth.html#manual-token-generation
    script_dir = os.path.dirname(os.path.realpath(__file__))
    token_json_file = options.token_json_file
    token = get_token(token_json_file)

    # e.g. course_id = "43589"
    course_id = options.course_id
    assert isinstance(course_id, int)

    roster_file = options.roster
    assignment_list = options.assignment_list

    # e.g. assignment_id = "280047"
    assignment_name = options.assignment_name
    assignment_id = options.assignment_id
    assignment_name, assignment_id = get_assignment_name_and_id(assignment_name, assignment_id, assignment_list)

    download_directory = options.download_directory

    # e.g. user_id = "44648"
    netid = options.netid
    user_id = options.user_id
    netid, user_id = get_netid_and_user_id(netid, user_id, roster_file)

    # download assignment info
    url = build_canvas_url(["courses", course_id, "assignments", assignment_id], params={})
    assignment_response = open_canvas_page_as_string(url, token)
    assignment_response = json.loads(assignment_response)
    assignment_summary_path = os.path.join(download_directory, "assignment.json")
    with open(assignment_summary_path, "w") as f:
        json.dump(assignment_response, f)

    url = build_canvas_url(["courses", course_id, "assignments", assignment_id, "submissions", user_id], params={})
    response = open_canvas_page_as_string(url, token)
    response = json.loads(response)

    # only download new submissions
    submission_summary_file = "submission.json"
    submission_summary_path = os.path.join(download_directory, submission_summary_file)
    if os.path.isfile(os.path.join(download_directory, submission_summary_file)):
        submission_summary = {}
        with open(submission_summary_path, "r") as f:
            submission_summary = json.load(f)

        local_submitted_at = datetime.datetime.strptime(submission_summary["submitted_at"], "%Y-%m-%dT%H:%M:%SZ").timetuple()

        if response["submitted_at"] != "null":
            remote_submitted_at = datetime.datetime.strptime(response["submitted_at"], "%Y-%m-%dT%H:%M:%SZ").timetuple()

            if not (remote_submitted_at > local_submitted_at):
                # if the submission is not newer than the one we already have, skip it
                msg = "%s: remote submission [%s] not newer than local submission [%s]. Exiting." % \
                      (__file__, submission_summary["submitted_at"], response["submitted_at"])
                print(msg)
                write_to_log(msg)
                sys.exit(1)

    if "attachments" not in response:
        msg = "%s: No attachments submitted for netid [%s] user_id [%s]. Exiting." % (__file__, netid, user_id)
        print(msg)
        write_to_log(msg)
        sys.exit(2)

    attachments = response["attachments"]

    if len(attachments) != 1:
        msg = "%s: Expected 1 attachment, got [%s]. Exiting." % (__file__, len(attachments))
        print(msg)
        write_to_log(msg)
        sys.exit(3)

    # if we get this far, we're doing the download
    file_url = attachments[0]["url"]
    if not os.path.isdir(download_directory):
        os.mkdir(download_directory, 0755)

    filename = options.download_filename
    if filename is None:
        filename = attachments[0]["filename"]

    download_path = os.path.join(download_directory, filename)

    request = urllib2.Request(file_url)
    download_response = urllib2.urlopen(request)
    with open(download_path, "wb") as local_file:
        local_file.write(download_response.read())

    # update summary file and history file (list of all summaries)
    submissions_history_file = "submissions_history.json"
    submissions_history_path = os.path.join(download_directory, submissions_history_file)
    if os.path.isfile(submissions_history_path):
        with open(submissions_history_path, "r") as f:
            submissions_history = json.load(f)
    else:
        submissions_history = []

    submissions_history.append(response)
    with open(submissions_history_path, "w") as f:
        json.dump(submissions_history, f)

    with open(submission_summary_path, "w") as f:
        json.dump(response, f)

