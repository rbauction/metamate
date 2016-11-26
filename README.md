# metamate
Salesforce metadata management tool

The tool is currently only capable of verifying a deployment package by deploying it with [checkOnly] (https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_deploy.htm) parameter set to **true** and running a subset of tests. This is done to speed up testing step in the CI workflow (run a subset of tests instead of all tests).

The tool uses [sfdclib Python library] (https://github.com/rbauction/sfdclib) to manipulate Salesforce metadata.

Names of the Apex classes that get tested are extracted from the deployment package.

 - If deployment package contains a test class it will be added to the list of classes to test.
 - For non-test classes the tool will build a dependency map for all test classes it can find in the source directory and then check whether any non-test classes from the deployment package are referenced by test classes. If there is a match the corresponding test class(es) will be added to the list of classes to test.

Example
---
##### Deployment package contents
 - RealClass
 - UnrealClass
 - TestableClassTest

##### Source directory contents (classes directory)
 - RealClass
 - RealClassTest (references RealClass)
 - UnrealClass
 - TestableClass
 - TestableClassTest (references TestableClass)

##### Classes to be tested
 - RealClassTest
 - TestableClassTest

Installation
---
#### Linux, UNIX and Mac OS
Install Python v3.4, install [sfdclib Python library] (https://github.com/rbauction/sfdclib) and clone this repository.
```sh
pip install sfdclib
git clone https://github.com/rbauction/metamate.git
```

#### Windows
Download executable file from [releases] (https://github.com/rbauction/metamate/releases) tab or follow the instruction above.

How to create Windows executable
---
Install PyInstaller and then run the following command:
```sh
pyinstaller --onefile metamate.py
```
Resulting exe file can be found in dist directory.

Usage
---
```sh
usage: metamate.py [-h] [--username USERNAME] [--password PASSWORD]
                   [--token TOKEN] [--deploy-zip DEPLOY_ZIP]
                   [--source-dir SOURCE_DIR] [--sandbox] [--version VERSION]
                   command
```

##### Deploy a deployment package (ZIP file) (Windows, Linux, UNIX and Mac OS)
```sh
# Validate deployment package (Windows, Linux, UNIX and Mac OS)
python metamate.py deploy --check-only --sandbox --username sfdcadmin@mydomain.com.sandbox --password Password --deploy-zip ../deploy.zip

# Deploy using default Metadata API version (Windows, Linux, UNIX and Mac OS)
python metamate.py deploy --sandbox --username sfdcadmin@mydomain.com.sandbox --password Password --deploy-zip ../deploy.zip

# Specify Metadata API version and token (Windows, Linux, UNIX and Mac OS)
python metamate.py deploy --sandbox --version 37.0 --username sfdcadmin@mydomain.com.sandbox --password Password --token TOKEN --deploy-zip ../deploy.zip

# Deploy using default Metadata API version (Windows only)
metamate.exe deploy --sandbox --username sfdcadmin@mydomain.com.sandbox --password Password --deploy-zip ..\deploy.zip
```

##### Run unit tests contained in a deployment package (ZIP file) (Windows, Linux, UNIX and Mac OS)
```sh
python metamate.py deploy --check-only --test-level RunSpecifiedTests --sandbox --username sfdcadmin@mydomain.com.sandbox --password Password --deploy-zip ../deploy.zip --source-dir ../src
```
