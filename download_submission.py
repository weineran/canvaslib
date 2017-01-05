from optparse import OptionParser
import urllib2
import json
import os
import csv
import sys
#from autograde import get_file_local_or_full


parser = OptionParser(usage="Usage: %prog [options]",
                      description="Download a single submission.")
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
                  dest="download_directory", default="./",
                  help="The path to download the submission to.")
parser.add_option("-n", "--netid",
                  dest="netid", default=None,
                  help="The netid of the student whose assignment you wish to download.")
parser.add_option("-u", "--user-id",
                  dest="user_id", default=None, type=int,
                  help="The Canvas user_id of the student whose assignment you wish to download.")
parser.add_option("-r", "--roster",
                  dest="roster", default=None, type=str,
                  help="The path to a .csv file containing a class roster.  At a minimum, should have columns labeled "
                       "'netid' and 'user_id'.")
parser.add_option("-L", "--assignment_list",
                  dest="assignment_list", default=None, type=str,
                  help="The path to a .csv file containing a list of assignments.  At a minimum, should have columns labeled "
                       "'assignment_name' and 'assignment_id'.")
parser.add_option("-t", "--token-json-file",
                  dest="token_json_file", default=None, type=str,
                  help="The path to a .json file containing the Canvas authorization token.")


def get_attribute_from_csv_using_search_attribute(search_key, search_value, target_key, csv_file):
    assert os.path.isfile(csv_file)

    with open(csv_file) as f:
        reader = csv.DictReader(f) # values in the first row of the csvfile will be used as the fieldnames.
        for row in reader:
            if str(row[search_key]).lower() == str(search_value).lower():
                return row[target_key]

    raise Exception("Key [" + search_key + "] not found in csv file [" + csv_file + "]")


def get_assignment_id_from_assignment_name(assignment_name, assignment_list):
    search_key = "assignment_name"
    search_value = assignment_name
    target_key = "assignment_id"
    assignment_id = int(get_attribute_from_csv_using_search_attribute(search_key, search_value, target_key, assignment_list))

    return assignment_id


def get_assignment_name_from_assignment_id(assignment_id, assignment_list):
    search_key = "assignment_id"
    search_value = assignment_id
    target_key = "assignment_name"
    assignment_name = get_attribute_from_csv_using_search_attribute(search_key, search_value, target_key, assignment_list)

    return assignment_name


def get_assignment_name_and_id(assignment_name, assignment_id, assignment_list):
    assert (assignment_name != None or assignment_id != None), "assignment_name and assignment_id cannot both be None"

    if assignment_name != None:
        assert isinstance(assignment_name, str), "assignment_name is not a string: %s" % assignment_name
    if assignment_id != None:
        assert isinstance(assignment_id, int), "assignment_id is not an int: %s" % assignment_id

    if assignment_name != None and assignment_id != None:
        return assignment_name, assignment_id
    if assignment_name != None:
        return assignment_name, get_assignment_id_from_assignment_name(assignment_name, assignment_list)
    if assignment_id != None:
        return get_assignment_name_from_assignment_id(assignment_id, assignment_list), assignment_id


def get_user_id_from_netid(netid, roster_file):
    search_key = "netid"
    search_value = netid
    target_key = "user_id"
    user_id = int(get_attribute_from_csv_using_search_attribute(search_key, search_value, target_key, roster_file))

    return user_id


def get_netid_from_user_id(user_id, roster_file):
    search_key = "user_id"
    search_value = user_id
    target_key = "netid"
    netid = get_attribute_from_csv_using_search_attribute(search_key, search_value, target_key, roster_file)

    return netid


def get_netid_and_user_id(netid, user_id, roster_file):
    assert (netid != None or user_id != None), "netid and user_id cannot both be None"

    if netid != None:
        assert isinstance(netid, str), "netid is not a string: %s" % netid
    if user_id != None:
        assert isinstance(user_id, int), "user_id is not an int: %s" % user_id

    if netid != None and user_id != None:
        return netid, user_id
    if netid != None:
        # use netid to look up user_id
        return netid, get_user_id_from_netid(netid, roster_file)
    if user_id != None:
        # use user_id to look up netid
        return get_netid_from_user_id(user_id, roster_file), user_id


def get_filename(assignment_name):
    assert isinstance(assignment_name, str)
    return "xv6_" + assignment_name.replace(" ", "_") + ".tar.gz"


def get_token_from_json_file(token_json_file):
    assert os.path.isfile(token_json_file), "token_json_file is not a file: %s" % token_json_file

    with open(token_json_file) as f:
        token_dict = json.load(f)
        token = token_dict["token"]

    return token


if __name__ == "__main__":
    # example call:
    # python download_submission.py -c 43589 --assignment-id 280047 -u 44648 -r ../test_roster.csv -L ../test_assignment_list.csv

    (options, args) = parser.parse_args()

    # for token generation, see https://canvas.instructure.com/doc/api/file.oauth.html#manual-token-generation
    script_dir = os.path.dirname(os.path.realpath(__file__))
    #token_json_file = get_file_local_or_full(script_dir, options.token_json_file)
    token_json_file = options.token_json_file
    token = get_token_from_json_file(token_json_file)

    #course_id = "43589"
    course_id = options.course_id
    assert isinstance(course_id, int)

    #roster_file = get_file_local_or_full(script_dir, options.roster)
    roster_file = options.roster
    #assignment_list = get_file_local_or_full(script_dir, options.assignment_list)
    assignment_list = options.assignment_list

    #assignment_id = "280047"
    assignment_name = options.assignment_name
    assignment_id = options.assignment_id
    assignment_name, assignment_id = get_assignment_name_and_id(assignment_name, assignment_id, assignment_list)

    #user_id = "44648"
    netid = options.netid
    user_id = options.user_id
    netid, user_id = get_netid_and_user_id(netid, user_id, roster_file)

    url = "https://canvas.northwestern.edu/api/v1/courses/" + str(course_id) + "/assignments/" + str(assignment_id) + \
          "/submissions/" + str(user_id)
    request = urllib2.Request(url)
    #base64string = base64.b64encode('%s' % token)
    request.add_header("Authorization", "Bearer %s" % token)
    response = urllib2.urlopen(request).read()
    response = json.loads(response)

    print(response)
    print("")
    if "attachments" not in response:
        print("No attachments submitted for " + netid + ".  Exiting.")
        sys.exit(1)

    attachments = response["attachments"]
    print(attachments)

    if len(attachments) != 1:
        print("number of attachments: " + len(attachments))
        print("exiting")
        sys.exit(2)

    file_url = attachments[0]["url"]

    # if we get here, we're doing the download
    download_directory = options.download_directory
    if not os.path.isdir(download_directory):
        os.mkdir(download_directory, 0755)

    filename = get_filename(assignment_name)
    download_path = os.path.join(download_directory, filename)

    request = urllib2.Request(file_url)
    #request.add_header("Authorization", "Bearer %s" % token)
    response = urllib2.urlopen(request)
    with open(os.path.basename(download_path), "wb") as local_file:
        local_file.write(response.read())

    # TODO in this script create download_directory