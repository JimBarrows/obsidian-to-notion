Feature: README Documentation
  As a developer
  I want the README to have correct Python command examples
  So that I can successfully set up and run the project

  Scenario: README uses python3 command for virtual environment setup
    Given I have the README.md file
    When I look for virtual environment setup instructions
    Then the command should use "python3" not "python"

  Scenario: README uses python3 command for dry-run example
    Given I have the README.md file
    When I look for dry-run command examples
    Then the command should use "python3" not "python"

  Scenario: README uses python3 command for migration execution
    Given I have the README.md file
    When I look for migration execution examples
    Then the command should use "python3" not "python"

  Scenario: All Python commands in README use python3
    Given I have the README.md file
    When I search for all Python command examples
    Then all commands should use "python3" not "python"
    And there should be no instances of "python " without the "3"
