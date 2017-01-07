import json
import urllib2
import os
import csv


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


def open_canvas_page(url, token):
    assert isinstance(url, str)
    assert isinstance(token, str)

    request = urllib2.Request(url)
    request.add_header("Authorization", "Bearer %s" % token)
    page = urllib2.urlopen(request)

    return page


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
        response = page.read().decode("unicode-escape").encode("ascii", "ignore")
        #response = response.decode()
        #print(response)
        response = json.loads(response)

        for user in response:
            mylist.append(user)

        should_continue, url = get_next_page_url(page)


def write_list_to_csv(mylist, destination):
    assert isinstance(mylist, list), "mylist is not a list: %s" % mylist
    assert isinstance(destination, str), "destination is not a string: %s" % destination

    with open(destination, "w") as f:
        writer = csv.DictWriter(f, fieldnames=mylist[0].keys())

        writer.writeheader()
        for item in mylist:
            writer.writerow(item)


def build_canvas_url(api_subdirectories, page_num):
    url = "https://canvas.northwestern.edu/api/v1"

    for subdir in api_subdirectories:
        url += "/" + str(subdir)

    url += "?page=" + str(page_num)

    return url


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


def get_attribute_from_csv_using_search_attribute(search_key, search_value, target_key, csv_file):
    assert os.path.isfile(csv_file)

    with open(csv_file) as f:
        reader = csv.DictReader(f) # values in the first row of the csvfile will be used as the fieldnames.
        for row in reader:
            if str(row[search_key]).lower() == str(search_value).lower():
                return row[target_key]

    raise Exception("Key-value [" + search_key + "=" + str(search_value) + "] not found in csv file [" + csv_file + "]")


def get_assignment_id_from_assignment_name(assignment_name, assignment_list):
    search_key = "name"
    search_value = assignment_name
    target_key = "id"
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