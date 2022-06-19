Feature: Webm converter testing

    Background: Initiate Platform Interface
        Given Platform Interface is initialized as dlp and Environment is set according to git branch
        And There is a project by the name of "webm_test"
        And There is a dataset by the name of "webm_test"


    Scenario: Upload a single item success
        When I upload a file in path "success.mp4"
        Then item is clean
        Then i run a converter in it
        Then i check the item success
        Then i delete the project

    Scenario: Upload a single item fail
        When I upload a file in path "fail.avi"
        Then item is clean
        Then i run a converter in it
        Then i check the item fail
        Then i delete the project