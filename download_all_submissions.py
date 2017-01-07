from optparse import OptionParser
import os
import subprocess
from utils import get_token, download_all_objects_to_list, get_assignment_name_and_id, get_netid_from_user_id, \
                  build_canvas_url, make_new_directory


parser = OptionParser(usage="Usage: %prog [options]",
                      description="Download all students' submissions for a given assignment.  Not all arguments are "
                                  "required.  For example, try:                                                  "
                                  "$ python " + __file__ + " -c <course_id> -a <assignment_name>")
parser.add_option("-c", "--course-id",
                  dest="course_id", default=None, type=int,
                  help="The Canvas course_id.  e.g. 43589")
parser.add_option("-a", "--assignment-name",
                  dest="assignment_name", default=None,
                  help="The name of the assignment to download.  e.g. 'proj4'")
parser.add_option("-i", "--assignment-id",
                  dest="assignment_id", default=None, type=int,
                  help="The Canvas assignment_id of the assignment to download.")
parser.add_option("-d", "--parent-directory",
                  dest="parent_directory", default="submissions/",
                  help="The path to download the submissions to.  Each submission will be downloaded to a subdirectory "
                       "of the parent directory: <parent_directory>/<netid>/<assignment_name>/")
parser.add_option("-r", "--roster",
                  dest="roster", default=os.path.join("resources","roster.csv"), type=str,
                  help="The path to a .csv file containing a class roster.  At a minimum, should have columns labeled "
                       "'login_id' (e.g. awp066) and 'id' (the Canvas user_id).")
parser.add_option("-L", "--assignment_list",
                  dest="assignment_list", default=os.path.join("resources","assignments.csv"), type=str,
                  help="The path to a .csv file containing a list of assignments.  At a minimum, should have columns labeled "
                       "'name' and 'id'.")
parser.add_option("-t", "--token-json-file",
                  dest="token_json_file", default=os.path.join("resources","token.json"), type=str,
                  help="The path to a .json file containing the Canvas authorization token.")


def get_or_make_directory(parent_directory, subdirectory):
    assert os.path.isdir(parent_directory), "parent_directory is not a directory: %s" % parent_directory

    target_directory = os.path.join(parent_directory, subdirectory)
    if os.path.isdir(target_directory):
        return target_directory
    else:
        os.mkdir(target_directory, 0755)
        return target_directory


def build_submissions_url(course_id, assignment_id, page_num):
    api_subdirectories = ["courses", course_id, "assignments", assignment_id, "submissions"]
    url = build_canvas_url(api_subdirectories, page_num)

    return url


if __name__ == "__main__":
    (options, args) = parser.parse_args()

    course_id = options.course_id
    assert isinstance(course_id, int), "course_id is not an int: %s" % course_id

    script_dir = os.path.dirname(os.path.realpath(__file__))

    token_json_file = options.token_json_file
    assert os.path.isfile(token_json_file), "token_json_file is not a file: %s" % token_json_file

    roster_file = options.roster
    assert os.path.isfile(roster_file), "roster_file is not a file: %s" % roster_file

    parent_directory = options.parent_directory
    if not os.path.isdir(parent_directory):
        parent_directory = make_new_directory("parent_directory", parent_directory)

    assignment_list = options.assignment_list
    assert os.path.isfile(assignment_list), "assignment_list is not a file: %s" % assignment_list

    assignment_name = options.assignment_name
    assignment_id = options.assignment_id

    assignment_name, assignment_id = get_assignment_name_and_id(assignment_name, assignment_id, assignment_list)

    token = get_token(token_json_file)
    url = build_submissions_url(course_id, assignment_id, page_num=1)
    submissions = []
    download_all_objects_to_list(url, token, mylist=submissions)

    plist = {}
    for submission in submissions:
        user_id = submission["user_id"]
        netid = get_netid_from_user_id(user_id, roster_file)

        if len(netid) < 1 or len(str(user_id)) < 1:
            print("skipping netid: " + str(netid) + " user_id: " + str(user_id))
            continue

        netid_directory = get_or_make_directory(parent_directory, netid)
        assignment_directory = os.path.join(netid_directory, assignment_name)

        args = ["python", "download_submission.py",
                  "-c", str(course_id),
                  "-a", assignment_name,
                  "-i", str(assignment_id),
                  "-u", str(user_id),
                  "-n", netid,
                  "-r", roster_file,
                  "-L", assignment_list,
                  "-d", assignment_directory,
                  "-t", token_json_file]
        args_as_string = " ".join(args)
        #print("calling " + args_as_string)
        p = subprocess.Popen(args)
        plist[netid] = p

    for netid in plist:
        p = plist[netid]
        p.wait()
        #print(netid + " " + str(p.returncode))


