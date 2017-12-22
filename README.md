# Jama Software
Jama Software is the definitive system of record and action for product development. The company’s modern requirements and test management solution helps enterprises accelerate development time, mitigate risk, slash complexity and verify regulatory compliance. More than 600 product-centric organizations, including NASA, Boeing and Caterpillar use Jama to modernize their process for bringing complex products to market. The venture-backed company is headquartered in Portland, Oregon. For more information, visit [jamasoftware.com](http://jamasoftware.com).

Please visit [dev.jamasoftware.com](http://dev.jamasoftware.com) for additional resources and join the discussion in our community [community.jamasoftware.com](http://community.jamasoftware.com).

## Embedded Item-Links Relationship Manager
Users often embed links in Jama items to other Jama items in the same instance. These embedded links to other items are typically related to each other as well. This script ensures that the only relationships an item of a given item type has, are from items that are embedded as links in a certain field. This means that relationships to items not embedded as links within an item will be deleted, and relationships to all embedded item links are created. The embedded links to Jama items acts as the true record of truth that dictates what relationships a given item has. 
 
### How it works
The script loads a local configuration file that contains all the required fields in the [**Setup**] section below. 
   - If no projectID is specific, all items of a given item type are processed. If a projectID is specified, only items of a given item type that are contained within this project will be processed. 
   - The relationship type ID must coincide with the relationship rules configured for the Jama instance the script is pointed at. If a relationship cannot be created due to items being deleted, or invalid relationship type, a failure record will be recorded in *errors.log*.
   - The item type ID must be set to determine what type of items will be processed by the script
   - The field in which embedded links to Jama items are contained must be specified. 
To limit the number of processed items, the application will attempt to load a local *last_run.cfg* file that contains the date/time of the application's last run. If no such file exists, all items of the specified item type will be processed. Every time the application runs, the *last_run.cfg* is updated with the latest run date/time. 

All items of the specified item type within the project(s) specified, will be retrieved from Jama's server. These items are then filtered to only include items that have been modified since the *last_run* date. If no *last_run* is retrieved, all items will be processed. The application will cycle through the filtered items and compare the upstream related items and the items that are embedded as links within the specified field. All relationships to items that are not embedded as links will be deleted, and upstream relationships will be established to each embedded linked item. A record of every relationship deletion/creation will be recorded in *updates.log*. All failures are included as records in *errors.log* along with information related to:
   - Relationship upstream item
   - Relationship downstream item
   - Relationship type (if applicable)
   - Relationship ID (if applicable)

Once the application is finished processing all items, *last_run.cfg* is updated/created and the run's date is recorded. 
### Authentication
In order to use this application, SAML must be enabled on the Jama instance it will be run against, so OAuth credentials can be used. Users are able to download the script and modify *jamaClient.py* to allow for basic authentication.
### Logs
A *logs* directory is created/updated every time the application is run. Within the main logs directory, a run-specific *timestamp* directory is created. Each run-specific directory contains two log files: 
- **errors.log** 
    - The error logs contain record entries contain information related to any and all failures that occur during a run. 
    - Failures include records of all relationships that could not be created and/or deleted. 
    - The logs will contain detailed information about the items related to each failed relationship creation/deletion for manual inspection. 
- **updates.log**
    - The update logs contain record entries for:
        - the number of items to be processed by the application
        - the number of relationships to be created
        - the number of relationships to be deleted
    - These logs will record whether or not every item that should be processed has been successfully processed or not. 
    - All errors that occur during processing will be recorded in the *errors* log. 

Please note that this script is distrubuted as-is as an example and will likely require modification to work for your specific use-case. Jama Support will not assist with the use or modification of the script.

## Before you begin
- Install Python 2.7 or newer
- Verify pip is installed (located under Scripts in your Python executable directory). If not, install pip
- Install the following packages using pip:
    * requests
    * python-dateutil
    * bs4
    * ConfigParser

## Setup
a. As always, set up a test environment and project to test the script.

b. Rename credentials.cfg.dst to credentials.cfg and fill in the following fields:
   1. __Required__
        - ```baseURL``` - e.g. https://jama-instance.jamacloud.com 
        - ```clientID```
        - ```clientSecret```
        - ```relationshipTypeID``` - Jama relationship type ID
        - ```itemTypeID``` - Jama item type ID
        - ```fieldWithLinks``` - Item type field that contains links to other Jama items
  
   2. __optional__
        - ```projectID``` - Restrict operation to a certain Jama project