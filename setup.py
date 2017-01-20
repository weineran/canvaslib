from optparse import OptionParser
import json
import os
import subprocess


parser = OptionParser(usage="Usage: %prog",
                      description="Creates the necessary resources to use canvaslib.                             "
                                  "Resources include:                                                            "
                                  "* resources/token.json                                                        "
                                  "* resources/roster.csv                                                        "
                                  "* resources/assignments.csv")


def exit_setup():
    print("")
    print("Setup complete")
    exit()


def download_roster(course_id):
    p = subprocess.Popen(["python", "download_roster.py",
                          "-c", str(course_id)])
    p.wait()


def download_assignments(course_id):
    p = subprocess.Popen(["python", "download_assignments.py",
                          "-c", str(course_id)])
    p.wait()


def write_token_to_json(token, token_filename):
    json.dump(token_dict, open(token_filename, "w"))
    print("Your token has been saved to '" + resources_dir + "/" + token_filename + "'")


if __name__ == "__main__":
    (options, args) = parser.parse_args()

    print("")
    print("To use this library, you will need a Canvas token.")
    print("Instructions on how to generate a token can be found here:")
    print("https://canvas.instructure.com/doc/api/file.oauth.html#manual-token-generation")
    print("")
    print("Here are the quick instructions.")
    print("1) Go here: https://canvas.northwestern.edu/profile/settings")
    print("2) Click the blue button that says 'New Access Token'.")
    print("")
    print("Once you have a token, paste it here.")
    token = raw_input("token> ")

    token_dict = {}
    token_dict["token"] = str(token)

    resources_dir = "resources"
    if not os.path.isdir(resources_dir):
        os.mkdir(resources_dir, 0600)

    token_filename = os.path.join(resources_dir, "token.json")

    if not os.path.isfile(token_filename):
        write_token_to_json(token, token_filename)
    else:
        print("It appears that '" + token_filename + "' already exists.  Would you like to overwrite it?")
        should_overwrite = raw_input("Overwrite? (y/n)> ")

        if should_overwrite.lower() == "y" or should_overwrite.lower() == "yes":
            write_token_to_json(token, token_filename)

    print("")
    print("Please enter the course ID of the course.")
    print("For example, if your Canvas course homepage is 'https://canvas.northwestern.edu/courses/49815', then "
          "the course ID is '49815'.")
    course_id = int(raw_input("Course ID> "))

    print("")
    print("Would you like to download the roster for your course?")
    should_download = raw_input("Download roster? (y/n)> ")
    if should_download.lower() == "y" or should_download.lower() == "yes":
        download_roster(course_id)

    print("")
    print("Would you like to download the list of assignments for your course?")
    should_download = raw_input("Download assignment list? (y/n)> ")
    if should_download.lower() == "y" or should_download.lower() == "yes":
        download_assignments(course_id)

    exit_setup()
