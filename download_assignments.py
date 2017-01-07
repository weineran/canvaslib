from optparse import OptionParser
import os
from utils import get_token, download_all_objects_to_list, write_list_to_csv, build_canvas_url


parser = OptionParser(usage="Usage: %prog [options]",
                      description="Download the list of assignments to assignments.csv.")
parser.add_option("-c", "--course-id",
                  dest="course_id", default=None, type=int,
                  help="The Canvas course_id.  e.g. 43589")
parser.add_option("-t", "--token-json-file",
                  dest="token_json_file", default=os.path.join("resources", "token.json"), type=str,
                  help="The path to a .json file containing the Canvas authorization token.")


def build_assignments_url(course_id, page_num):
    api_subdirectories = ["courses", course_id, "assignments"]
    url = build_canvas_url(api_subdirectories, page_num)

    return url


if __name__ == "__main__":
    (options, args) = parser.parse_args()

    course_id = options.course_id
    assert isinstance(course_id, int), "course_id is not an int: %s" % course_id

    token_json_file = options.token_json_file
    assert os.path.isfile(token_json_file), "token_json_file is not a file: %s" % token_json_file

    assignments_file = os.path.join("resources", "assignments.csv")
    if os.path.isfile(assignments_file):
        print("It appears that '" + assignments_file + "' already exists.  Would you like to overwrite it?")
        should_overwrite = raw_input("Overwrite? (y/n)> ")

        if should_overwrite.lower() != "y" and should_overwrite.lower() != "yes":
            print("download_assignments.py canceled.  Exiting.")
            exit()

    url = build_assignments_url(course_id, page_num=1)
    token = get_token(token_json_file)
    assignments = []
    download_all_objects_to_list(url, token, mylist=assignments)

    write_list_to_csv(mylist=assignments, destination=assignments_file)

    print("Assignment list has been downloaded to " + assignments_file)
