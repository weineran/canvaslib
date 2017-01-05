import json
import os

if __name__ == "__main__":
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
    token = raw_input("token>")

    token_dict = {}
    token_dict["token"] = str(token)

    filename = "token.json"

    if os.path.isfile(filename):
        print("It appears that '" + filename + "' already exists.  Would you like to overwrite it?")
        should_overwrite = raw_input("overwrite? (y/n) >")

        if should_overwrite.lower() != "y" and should_overwrite.lower() != "yes":
            print("Setup canceled.  Exiting.")
            exit()

    json.dump(token_dict, open(filename, "w"))
    print("Your token has been saved to the current directory as '" + filename + "'")

    print("Setup complete.")