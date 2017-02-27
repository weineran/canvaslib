from optparse import OptionParser
import os
from utils import get_assignment_name_and_id, get_netid_and_user_id, build_canvas_url, open_canvas_page_as_string, \
                  get_token, post_file_using_curl, get_header, put_using_curl, write_to_log
import time, datetime
import json
import sys


parser = OptionParser(usage="Usage: %prog [options]",
                      description="Upload a results file along with a submission comment.  Not all arguments are required.                "
                                  "For example, try:                                                             "
                                  "python " + __file__ + " -c <course_id> -a <assignment_name> -l <netid> -f <file-to-upload>")
parser.add_option("-c", "--course-id",
                  dest="course_id", default=None, type=int,
                  help="The Canvas course_id.  e.g. 43589")
parser.add_option("-f", "--results_file",
                  dest="results_file", default=None,
                  help="The path to the results file that will be uploaded.")
parser.add_option("-g", "--grade",
                  dest="grade", default=None, type=str,
                  help="The grade to award to the assignment submission.")
parser.add_option("-a", "--assignment-name",
                  dest="assignment_name", default=None,
                  help="The name of the assignment to download.  e.g. 'proj4'")
parser.add_option("-i", "--assignment-id",
                  dest="assignment_id", default=None, type=int,
                  help="The Canvas assignment_id of the assignment to download.")
parser.add_option("-l", "--login_id",
                  dest="login_id", default=None,
                  help="The login_id (netid) of the student whose assignment you wish to download.")
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

RETURNCODE_SUCCESS = 0
RETURNCODE_ALREADY_UPLOADED = 1
RETURNCODE_FAILED = 4


if __name__ == "__main__":
    (options, args) = parser.parse_args()

    course_id = options.course_id
    assert isinstance(course_id, int), "course_id is not an int: %s" % course_id

    results_file = options.results_file
    assert results_file is not None, "results_file argument must be provided"
    assert os.path.isfile(results_file), "results_file is not a valid file: %s" % results_file

    grade = options.grade
    if grade:
        assert isinstance(grade, str), "grade is not a string: %s" % grade

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

    token_json_file = options.token_json_file
    token = get_token(token_json_file)

    # upload file in 3 steps
    # (https://canvas.instructure.com/doc/api/file.file_uploads.html#method.file_uploads.post)
    # step 1
    url = build_canvas_url(["courses", course_id, "assignments", assignment_id, "submissions", user_id, "comments",
                            "files"], params={})
    results_filename = os.path.basename(results_file)
    size = os.stat(results_file).st_size
    timestamp = datetime.datetime.fromtimestamp(time.time())
    post_data = {"name": "%s_%s_%s" % (login_id[:8], timestamp.strftime('%Y-%m-%d_%H.%M.%S'), results_filename),
                 "size": size,}
    response = open_canvas_page_as_string(url, token, data=post_data)
    response = json.loads(response)
    print(response)

    # step 2
    upload_url = str(response["upload_url"])
    upload_params = response["upload_params"]
    files = {"file": results_file}

    response2, headers = post_file_using_curl(upload_url, data=upload_params, file=results_file)
    print('response 2')
    print(response2)
    print("headers")
    print(headers)

    # step 3
    location = get_header("Location", headers)
    print("location: %s" % location)

    response3 = open_canvas_page_as_string(str(location), token, method="POST")
    print("response 3")
    print(response3)

    # upload comment and attach the previously uploaded file
    comment_url = build_canvas_url(["courses", course_id, "assignments", assignment_id, "submissions", user_id])
    upload_id = json.loads(response3)["id"]
    comment_text = "results attached " + timestamp.strftime('%Y-%m-%d %H:%M:%S')
    put_data = {"comment[text_comment]": comment_text, "comment[file_ids][]": upload_id}

    if grade:
        put_data["submission[posted_grade]"] = grade

    print(put_data)
    response4, headers = put_using_curl(comment_url, token, data=put_data)
    print(response4)

    try:
        json.loads(response4)
    except (ValueError, TypeError) as E:
        msg = "%s: final PUT request received non-json response [%s]" % (__file__, E)
        write_to_log(msg)
        print(msg)
        sys.exit(RETURNCODE_FAILED)
