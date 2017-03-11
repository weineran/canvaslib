import json
import urllib2, urllib
import os
import csv
from setup import download_assignments
import urllib2_extension
import subprocess
import sys
from optparse import OptionParser


log_filename = "canvaslib.log"


def convert_Z_to_UTC(time_string):
    assert isinstance(time_string, str), "time_string is not a string: %s" % time_string

    if time_string.endswith("Z"):
        time_string = time_string[:-1]
        time_string += "UTC"

    return time_string


def get_optparse_args(parser):
    assert isinstance(parser, OptionParser), "parser is not an OptionParser: %s" % parser

    (options, args) = parser.parse_args()
    default = None

    submissions_directory = getattr(options, "submissions_directory", default)
    assert isinstance(submissions_directory, str), "submissions_directory not provided? [%s]" % submissions_directory
    assert os.path.isdir(
        submissions_directory), "submissions_directory is not a valid directory: %s" % submissions_directory

    assignment_name = getattr(options, "assignment_name", default)
    assignment_id = getattr(options, "assignment_id", default)
    assert isinstance(assignment_name, str) or isinstance(assignment_id, int), \
        "A valid assignment_name or assignment_id must be provided.\n" \
        "assignment_name: [%s]\n" \
        "assignment_id: [%s]" % (assignment_name, assignment_id)

    user_id = getattr(options, "user_id", default)
    login_id = getattr(options, "login_id", default)
    assert isinstance(login_id, str) or isinstance(user_id, int), \
        "A valid login_id or user_id must be provided.\n" \
        "login_id: [%s]\n" \
        "user_id: [%s]" % (login_id, user_id)

    roster_file = getattr(options, "roster_file", default)
    #assert os.path.isfile(roster_file), "roster_file is not a valid file: %s" % roster_file

    assignment_list = getattr(options, "assignment_list", default)
    assert os.path.isfile(assignment_list), "assignment_list is not a valid file: %s" % assignment_list

    course_id = getattr(options, "course_id", default)

    assignment_name, assignment_id = get_assignment_name_and_id(assignment_name, assignment_id, assignment_list,
                                                                course_id)
    #login_id, user_id = get_netid_and_user_id(login_id, user_id, roster_file)

    return options, args, submissions_directory, assignment_name, assignment_id, user_id, login_id, roster_file, \
           assignment_list, course_id


def write_to_log(message):
    assert isinstance(message, str) or isinstance(message, unicode), "message is not a string: %s" % message

    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), log_filename)

    with open(file_path, "a") as f:
        f.write(message + "\n")


def post_multipart_form(url, data, files, headers=[]):
    assert isinstance(url, str), "url is not a string: %s" % url
    assert isinstance(data, dict), "data is not a dict: %s" % data
    assert isinstance(files, dict), "files is not a dict: %s" % files

    form = urllib2_extension.MultiPartForm()

    for field in data:
        form.add_field(field, data[field])

    for fieldname in files:
        this_file = files[fieldname]
        with open(this_file, "rb") as f:
            form.add_file(fieldname, this_file, f)

    request = urllib2.Request(url)

    for headername in headers:
        request.add_header(headername, headers[headername])

    body = str(form)
    request.add_data(body)

    return urllib2.urlopen(request)


def get_header(header_name, headers):
    assert isinstance(header_name, str), "header_name is not a string: %s" % header_name
    assert isinstance(headers, list), "headers is not a list: %s" % headers

    for header in headers:
        assert isinstance(header, str)
        if header.startswith(header_name + ":") or header.startswith(header_name.lower() + ":"):
            return header[len(header_name + ":"):].strip()

    return None


def put_using_curl(url, token, data):
    assert isinstance(url, str), "url is not a string: %s" % url
    assert isinstance(token, str), "token is not a string: %s" % token
    assert isinstance(data, dict), "data is not a dict: %s" % data

    headers = {"Authorization": "Bearer %s" % token}

    result, headers = do_curl(url, method="PUT", data=data, headers=headers)

    return result, headers


def do_curl(url, method=None, data={}, headers={}, files={}):
    assert isinstance(url, str), "url is not a string: %s" % url
    assert method in ["PUT", "GET", "POST", "HEAD", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH", None], \
        "Not a valid method: %s" % method
    if data:
        assert isinstance(data, dict), "data is not a dict: %s" % data
    if headers:
        assert isinstance(headers, dict), "headers is not a dict: %s" % headers
    if files:
        assert isinstance(files, dict), "files is not a dict: %s" % files

    args = ["curl"]

    if method:
        args.extend(["-X", method])

    args.append(url)

    if method == "PUT":
        data_flag = "-d"
    else:
        data_flag = "-F"

    for header_name in headers:
        #args.extend(["-H", header_name+"="+urllib.quote(str(headers[header_name]))])
        #args.extend(["-H", "\""+header_name + ": " + headers[header_name]+"\""])
        args.extend(["-H", header_name + ": " + headers[header_name]])

    for param_name in data:
        args.extend([data_flag, param_name+"="+urllib.quote(str(data[param_name]))])

    for param_name in files:
        args.extend([data_flag, param_name+"="+str(files[param_name])])

    headers_file = "resp_headers.txt"
    args.extend(["-D", headers_file])

    # args.append("-v")
    # args.extend(["--trace", "-"])

    print(" ".join(args))
    p = subprocess.Popen(args, stdout=subprocess.PIPE)
    p.wait()
    result = p.stdout.read()
    #result = subprocess.call(args)

    with open(headers_file, "r") as f:
        resp_headers = f.readlines()

    os.remove(headers_file)

    return result, resp_headers


def post_file_using_curl(url, data, file):
    assert isinstance(url, str), "url is not a string: %s" % url
    assert isinstance(data, dict), "data is not a dict: %s" % data
    assert os.path.isfile(file), "file is not a file: %s" % file

    args = ["curl", url]

    for param_name in data:
        args.append("-F")
        args.append(param_name+"="+str(data[param_name]))

    args.append("-F")
    args.append("file=@"+file)

    args.extend(["-D", "headers.txt"])

    print(" ".join(args))
    p = subprocess.Popen(args, stdout=subprocess.PIPE)
    p.wait()
    result = p.stdout.read()

    with open("headers.txt", "r") as f:
        headers = f.readlines()

    return result, headers


def make_new_directory(dir_name, path):
    assert isinstance(dir_name, str), "dir_name is not a string: %s" % dir_name
    assert isinstance(path, str), "path is not a string: %s" % path
    assert not os.path.isdir(path), "dir_name already exists: %s" % path

    print(dir_name + " [" + path + "] does not exist.  Would you like to create it?")
    should_create = raw_input("Create directory? (y/n)> ")

    if should_create.lower() == "y" or should_create.lower() == "yes":
        os.mkdir(path, 0755)
        return path
    else:
        print("Directory not created.  Exiting.")
        exit()


def get_token(token_json_file):
    assert os.path.isfile(token_json_file)

    with open(token_json_file) as t:
        token_dict = json.load(t)

    token = str(token_dict["token"])

    return token


def open_canvas_page(url, token, data=None, method=None):
    assert isinstance(url, str), "url is not a string: %s" % url
    assert isinstance(token, str), "token is not a string: %s" % token

    #request = urllib2.Request(url)
    request = urllib2_extension.MethodRequest(url, method)
    request.add_header("Authorization", "Bearer %s" % token)

    if data:
        request.add_data(urllib.urlencode(data))

    try:
        page = urllib2.urlopen(request)
    except urllib2.HTTPError as e:
        print(e)
        write_to_log(e)
        sys.exit(1)

    return page


def open_canvas_page_as_string(url, token, data=None, method=None):
    #return urllib.unquote(open_canvas_page(url, token, data, method).read())
    return open_canvas_page(url, token, data, method).read()


def are_more_pages_remaining(page):
    info = page.info()
    full_link = info.getheader("Link")
    links = full_link.split(",")

    for link in links:
        rel_current = 'rel="current"'
        rel_last = 'rel="last"'

        if rel_current in link:
            current_link = link[1:link.find(">")]
            continue

        if rel_last in link:
            last_link = link[1:link.find(">")]
            continue

    if current_link == last_link:
        more_remaining = False
    else:
        more_remaining = True

    return more_remaining


def get_next_page_url(page):
    info = page.info()
    full_link = info.getheader("Link")
    links = full_link.split(",")

    for link in links:
        rel_current = 'rel="current"'
        rel_last = 'rel="last"'
        rel_next = 'rel="next"'

        if rel_current in link:
            current_link = link[1:link.find(">")]
            continue

        if rel_last in link:
            last_link = link[1:link.find(">")]
            continue

        if rel_next in link:
            next_url = link[1:link.find(">")]
            continue

    if current_link == last_link:
        is_valid = False
        next_url = None
    else:
        is_valid = True
        assert isinstance(next_url, str)

    return is_valid, next_url


def download_all_objects_to_list(url, token, mylist):
    assert isinstance(url, str), "url is not a string: %s" % url
    assert isinstance(token, str), "token is not a string: %s" % token
    assert isinstance(mylist, list), "mylist is not a list: %s" % mylist

    should_continue = True

    while should_continue == True:
        page = open_canvas_page(url, token)
        response = page.read().decode('utf-8', "ignore").encode("ascii", "ignore")
        #response = response.decode("unicode-escape").encode("ascii", "ignore")
        #print(response)
        response = json.loads(response)

        for item in response:
            mylist.append(item)

        should_continue, url = get_next_page_url(page)

def write_header_row(writer, fieldnames):
    assert isinstance(writer, csv.DictWriter), "writer is not a DictWriter: %s" % writer
    assert isinstance(fieldnames, list), "fieldnames is not a list: %s" % fieldnames

    header_row = {}
    for fieldname in fieldnames:
        header_row[fieldname] = fieldname

    writer.writerow(header_row)

    return


def write_list_to_csv(mylist, destination):
    assert isinstance(mylist, list), "mylist is not a list: %s" % mylist
    assert isinstance(destination, str), "destination is not a string: %s" % destination

    with open(destination, "w") as f:
        fieldnames = mylist[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        # write header row
        # writer.writeheader()  # apparently this doesn't work in Python 2.6
        write_header_row(writer, fieldnames)

        for item in mylist:
            writer.writerow(item)


def build_canvas_url(api_subdirectories, params={}):
    assert isinstance(api_subdirectories, list)
    assert isinstance(params, dict)

    url = "https://canvas.northwestern.edu/api/v1"

    for subdir in api_subdirectories:
        url += "/" + str(subdir)

    if len(params) > 0:
        url += "?"
        params_list = [str(key) + "=" + str(params[key]) for key in params]
        url += "&".join(params_list)

    return url


def get_assignment_name_and_id(assignment_name, assignment_id, assignment_list, course_id=None):
    assert (assignment_name != None or assignment_id != None), "assignment_name and assignment_id cannot both be None"

    if assignment_name != None:
        assert isinstance(assignment_name, str), "assignment_name is not a string: %s" % assignment_name
    if assignment_id != None:
        assert isinstance(assignment_id, int), "assignment_id is not an int: %s" % assignment_id

    if assignment_name != None and assignment_id != None:
        return assignment_name, assignment_id
    if assignment_name != None:
        return assignment_name, get_assignment_id_from_assignment_name(assignment_name, assignment_list, course_id)
    if assignment_id != None:
        return get_assignment_name_from_assignment_id(assignment_id, assignment_list), assignment_id


def get_attribute_from_csv_using_search_attribute(search_key, search_value, target_key, csv_file):
    assert os.path.isfile(csv_file)

    with open(csv_file) as f:
        reader = csv.DictReader(f) # values in the first row of the csvfile will be used as the fieldnames.
        for row in reader:
            if str(row[search_key]).lower() == str(search_value).lower():
                return row[target_key]

    raise Exception("Key-value [" + search_key + "=" + str(search_value) + "] not found in csv file [" + csv_file + "]")


def get_assignment_id_from_assignment_name(assignment_name, assignment_list, course_id=None):
    search_key = "name"
    search_value = assignment_name
    target_key = "id"
    try:
        assignment_id = int(get_attribute_from_csv_using_search_attribute(search_key, search_value, target_key, assignment_list))
    except:
        print("Failed to get assignment_id from assignment_name.  Trying to resolve by downloading the latest assignment list from Canvas.")
        download_assignments(course_id)
        assignment_id = int(get_attribute_from_csv_using_search_attribute(search_key, search_value, target_key, assignment_list))

    return assignment_id


def get_assignment_name_from_assignment_id(assignment_id, assignment_list):
    search_key = "id"
    search_value = assignment_id
    target_key = "name"
    assignment_name = get_attribute_from_csv_using_search_attribute(search_key, search_value, target_key, assignment_list)

    return assignment_name


def get_user_id_from_netid(netid, roster_file):
    search_key = "login_id"
    search_value = netid
    target_key = "id"
    user_id = int(get_attribute_from_csv_using_search_attribute(search_key, search_value, target_key, roster_file))

    return user_id


def get_netid_from_user_id(user_id, roster_file):
    search_key = "id"
    search_value = user_id
    target_key = "login_id"
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
