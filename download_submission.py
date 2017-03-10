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
                  help="The name of the assignment to download.  e.g. 'proj4'.  Not necessary if assignment-id is "
                       "provided.")
parser.add_option("-i", "--assignment-id",
                  dest="assignment_id", default=None, type=int,
                  help="The Canvas assignment_id of the assignment to download.  Not necessary if assignment-name is "
                       "provided.")
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
parser.add_option("-m",
                  dest="make_assignment_directory", action="store_true", default=False,
                  help="If the directory <assignment_name> doesn't exist, should it be created?")



def get_filename(assignment_name, netid):
    # TODO remove this function?
    assert isinstance(assignment_name, str)
    if not isinstance(netid, str):
        netid = ""

    return "xv6_" + assignment_name.replace(" ", "_") + "_" + netid + ".tar.gz"


if __name__ == "__main__":

    # Get command line options
    (options, args) = parser.parse_args()

    script_dir = os.path.dirname(os.path.realpath(__file__))

    # for token generation, see https://canvas.instructure.com/doc/api/file.oauth.html#manual-token-generation
    token_json_file = roster_file = os.path.join(script_dir, "resources", "token.json")
    token = get_token(token_json_file)

    course_id = options.course_id    # e.g. course_id = "43589"
    assert isinstance(course_id, int)

    roster_file = os.path.join(script_dir, "resources", "roster.csv")
    assignment_list = os.path.join(script_dir, "resources", "assignments.csv")

    assignment_name = options.assignment_name
    assignment_id = options.assignment_id    # e.g. assignment_id = "280047"
    assignment_name, assignment_id = get_assignment_name_and_id(assignment_name, assignment_id, assignment_list)

    download_directory = options.download_directory

    netid = options.netid
    user_id = options.user_id    # e.g. user_id = "44648"
    netid, user_id = get_netid_and_user_id(netid, user_id, roster_file)

    make_assignment_directory = options.make_assignment_directory

    # download submission info
    url = build_canvas_url(["courses", course_id, "assignments", assignment_id, "submissions", user_id], params={})
    response = open_canvas_page_as_string(url, token)
    remote_submission_summary = json.loads(response)

    # only download new submissions
    submission_summary_file = "submission.json"
    local_submission_summary_path = os.path.join(download_directory, submission_summary_file)
    if os.path.isfile(os.path.join(download_directory, submission_summary_file)):
        local_submission_summary = {}
        with open(local_submission_summary_path, "r") as f:
            local_submission_summary = json.load(f)

        local_submitted_at = datetime.datetime.strptime(local_submission_summary["submitted_at"], "%Y-%m-%dT%H:%M:%SZ").timetuple()

        if remote_submission_summary["submitted_at"] != "null":
            remote_submitted_at = datetime.datetime.strptime(remote_submission_summary["submitted_at"], "%Y-%m-%dT%H:%M:%SZ").timetuple()

            if not (remote_submitted_at > local_submitted_at):
                # if the submission is not newer than the one we already have, skip it
                msg = "%s: remote submission [%s] not newer than local submission [%s] for netid [%s]. Exiting." % \
                      (__file__, remote_submission_summary["submitted_at"], local_submission_summary["submitted_at"], netid)
                print(msg)
                write_to_log(msg)
                sys.exit(1)

    if "attachments" not in remote_submission_summary:
        msg = "%s: No attachments submitted for netid [%s] user_id [%s]. Exiting." % (__file__, netid, user_id)
        print(msg)
        write_to_log(msg)
        sys.exit(2)

    attachments = remote_submission_summary["attachments"]

    if len(attachments) != 1:
        msg = "%s: Expected 1 attachment, got [%s]. Exiting." % (__file__, len(attachments))
        print(msg)
        write_to_log(msg)
        sys.exit(3)

    # if we get this far, we're doing the download
    # First, download assignment info
    url = build_canvas_url(["courses", course_id, "assignments", assignment_id], params={})
    assignment_response = open_canvas_page_as_string(url, token)
    assignment_response = json.loads(assignment_response)
    assignment_summary_path = os.path.join(download_directory, "assignment.json")

    if not os.path.isdir(download_directory) and make_assignment_directory:
        msg = "Creating directory: %s" % download_directory
        print(msg)
        write_to_log(msg)
        os.mkdir(download_directory, 0700)

    assert os.path.isdir(download_directory), "download_directory is not a valid directory: %s" % download_directory

    with open(assignment_summary_path, "w") as f:
        json.dump(assignment_response, f)

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

    submissions_history.append(remote_submission_summary)
    with open(submissions_history_path, "w") as f:
        json.dump(submissions_history, f)

    with open(local_submission_summary_path, "w") as f:
        json.dump(remote_submission_summary, f)

