from config import Config
from jamaClient import JamaClient
from bs4 import BeautifulSoup
import logging
from dateutil import parser


class Process:
    def __init__(self):
        self.jama_client = JamaClient()
        self.items = []
        self.jama_config = Config()
        self.jama_client.setConfig(self.jama_config)
        self.item_type_ID = self.jama_config.testCaseStepItemTypeID
        self.realtionship_type_ID = self.jama_config.relationshipTypeID
        self.updateCount = 0
        self.failedCount = 0
        self.totalCount = 0
        self.projectID = self.jama_config.projectID
        self.successfulPostRelationshipCount = 0
        self.failedToPostRelationshipCount = 0
        self.failedToDeleteRelationshipCount = 0
        self.successfulDeleteRelationshipCount = 0



    def post_for_access_token(self):
        self.jama_config.update_last_run_time()



    def process(self):
        self.useCaseField = self.jama_config.testCaseField
        if self.useCaseField.endswith("$"):
            self.useCaseField = self.useCaseField + str(self.item_type_ID)

        # Get All Projects
        if self.projectID != None:
            url = "abstractitems?project=" + str(self.projectID) + "&itemType=" + str(self.item_type_ID)
        else:
            url = "abstractitems?itemType=" + str(self.item_type_ID)
        items = self.jama_client.get_all(url)
        if items == None:
            self.jama_config.successLogger.log(logging.INFO, "No items retrieved from Jama for itemType [" + str(self.item_type_ID) + "]. No items to be processed.")
            return
        self.items = self.filter_items_from_last_run(items)
        if items == None:
            self.jama_config.successLogger.log(logging.INFO, "No items found with a lastModifiedDate newer than the last run date of [" + self.jama_config.last_run_time + "]. No items to be processed.")
            return

        self.totalCount = len(self.items)

        self.jama_config.successLogger.log(logging.INFO, "Total number of items to process [" + str(self.totalCount) + "]")

        for item in self.items:
            self.process_item(item)

        self.jama_config.successLogger.log(logging.INFO, "\n\n")
        self.jama_config.successLogger.log(logging.INFO, "Number of successfully updated [" + str(self.updateCount) + "] item(s)")
        self.jama_config.successLogger.log(logging.INFO, "Number of items with errors during updates [" + str(self.failedCount) + "]")
        self.jama_config.successLogger.log(logging.INFO, "Number of successfully created relationships [" + str(self.successfulPostRelationshipCount) + "]")
        self.jama_config.successLogger.log(logging.INFO, "Number of successfully deleted relationships [" + str(self.successfulDeleteRelationshipCount) + "]")
        self.jama_config.successLogger.log(logging.INFO, "Number of failed created relationships [" + str(self.failedToPostRelationshipCount) + "]")
        self.jama_config.successLogger.log(logging.INFO, "Number of failed deleted relationships [" + str(self.failedToDeleteRelationshipCount) + "]")
        if self.failedToPostRelationshipCount > 0:
            self.jama_config.failureLogger.log(logging.ERROR, "Number of relationships that failed to be created [" + str(self.failedToPostRelationshipCount) + "].")
        if self.failedToDeleteRelationshipCount > 0:
            self.jama_config.failureLogger.log(logging.ERROR, "Number of relationships that failed to be deleted [" + str(self.failedToDeleteRelationshipCount) + "].")
        if self.failedCount > 0:
            self.jama_config.failureLogger.log(logging.ERROR, "Number of items that failed to update [" + str(self.failedCount) + "/" + str(self.totalCount) + "].")
        self.jama_config.update_last_run_time()
        self.jama_config.successLogger.log(logging.INFO, "Finished...")
        exit(0)



    def process_item(self, item):
        upstream_related_items = self.extract_upstream_related(item["id"])
        linked_use_case_items = self.extract_field_linked_items(item["id"], item["fields"][self.useCaseField])

        value = self.cross_reference(upstream_related_items, linked_use_case_items, item)
        if value == True:
            self.updateCount = self.updateCount + 1
            self.jama_config.successLogger.log(logging.INFO, "Successfully updated item [" + str(item["id"]) + "]")
        elif value == False:
            self.failedCount = self.failedCount + 1
            self.jama_config.successLogger.log(logging.INFO, "Encountered failures when updating item [" + str(item["id"]) + "]. Check the error logs for more information.")
        else:
            lastRun = " [" + str(self.jama_config.last_run_time) + "]" if str(self.jama_config.last_run_time) != None else ""
            self.jama_config.successLogger.log(logging.INFO, "Item [" + str(item["id"]) + "] has not been modified since last run" + ". No update necessary.")



    def filter_items_from_last_run(self, items):
        toReturn = []
        for item in items:
            if self.is_newer(item["modifiedDate"]):
                toReturn.append(item)
        return toReturn



    def is_newer(self, lastModifiedDate):
        modifiedDate = parser.parse(str(lastModifiedDate).rstrip(".000+0000"))
        if self.jama_config.last_run_time == None or modifiedDate > self.jama_config.last_run_time:
            return True
        return False



    def extract_upstream_related(self, itemId):
        upstream_related_dict = []
        upstream_links = self.jama_client.get_upstream_related(itemId=itemId)
        for upstream_link in upstream_links:
            item = {}
            item.__setitem__("relationshipID", upstream_link["id"])
            item.__setitem__("upstreamItem", upstream_link["fromItem"])
            item.__setitem__("relationship", upstream_link)
            upstream_related_dict.append(item)
        self.jama_config.successLogger.log(logging.INFO, "Successfully extracted upstream related items for item [" + str(itemId) + "]")
        return upstream_related_dict




    def extract_field_linked_items(self, itemID, content):
        dictionary = []
        richText = BeautifulSoup(content, 'html.parser')
        if richText is not None:
            for link in richText.find_all('a'):
                item = {}
                item.__setitem__("id", self.parseId(link))
                item.__setitem__("link", link)
                dictionary.append(item)
        self.jama_config.successLogger.log(logging.INFO, "Successfully extracted linked items from [" + self.jama_config.testCaseField + "] field for item [" + str(itemID) + "]")
        return dictionary



    def cross_reference(self, upstream_related_items, field_link_items, item):
        patch = False
        found = False
        relationshipsToDelete = []
        relationshipsToPost = []

        ## Check all upstream related items are located in the field_link_items
        for upstream_related_item in upstream_related_items:
            for link_item in field_link_items:
                if upstream_related_item.get("upstreamItem") == link_item.get("id"):
                    found = True
                    break
            if found == False:
                relationshipsToDelete.append(upstream_related_item)
                patch = True
            found = False

        ## Check all field_link_items are valid upstream related items
        for link_item in field_link_items:
            for upstream_related_item in upstream_related_items:
                if upstream_related_item.get("upstreamItem") == link_item.get("id"):
                    found = True
                    break
            if found == False:
                relationshipsToPost.append(link_item)
                patch = True
            found = False

        if patch == True:
            self.jama_config.successLogger.log(logging.INFO, "Item [" + str(item["id"]) + "] upstream related items require an update...")
            success_delete = self.delete_relationships(relationshipsToDelete, item["id"])
            success_post = self.post_item_relationships(relationshipsToPost, item["id"])
            return success_delete or success_post
            # return "UPDATED"
        return None



    def post_item_relationships(self, upstream_links, item):
        relationships = []
        for upstream_link in upstream_links:
            relationship = self.create_relationship_post_payload(item, upstream_link["id"])
            if relationship is not None:
                relationships.append(relationship)

        return self.post(itemID=item, relationships=relationships)



    def post(self, itemID, relationships):
        success = None
        for relationship in relationships:
            relationshipID = self.jama_client.post_relationship(relationship)
            try:
                relationship_id = int(relationshipID)
                if relationship_id != None:
                    if success == None:
                        success = True
                    self.jama_config.successLogger.log(logging.INFO, "Created relationship [" + str(relationship_id) + "] for item [" + str(itemID) + "]")
                    self.successfulPostRelationshipCount = self.successfulPostRelationshipCount + 1
            except Exception as e:
                success = False
                self.jama_config.failureLogger.log(logging.ERROR, "Failed to create relationship [" + str(relationship) + "] for item [" + str(itemID) + "] due to [" + relationshipID + "]")
                self.failedToPostRelationshipCount = self.failedToPostRelationshipCount + 1
        return success


    def delete_relationships(self, upstream_related_items, itemID):
        success = None
        for relationship in upstream_related_items:
            response = self.jama_client.delete_relationship(relationship.get("relationshipID"))
            if response == None:
                if success == None:
                    success = True
                self.jama_config.successLogger.log(logging.INFO, "Successfully deleted relationship [" + str(relationship.get("relationship")) + "] to update item [" + str(itemID) + "]")
                self.successfulDeleteRelationshipCount = self.successfulDeleteRelationshipCount + 1
            else:
                success = False
                self.jama_config.failureLogger.log(logging.ERROR, "Failed to deleted relationship [" + str(relationship.get("relationship")) + "] for item [" + str(itemID) + "]")
                self.failedToDeleteRelationshipCount = self.failedToDeleteRelationshipCount + 1
        return success


    def parseId(self, item):
        try:
            string_starting_with_id = str(item)[str(item).index("docId=") + 6:]
            item_id = string_starting_with_id[:string_starting_with_id.index("\" target")]
            # self.jama_config.successLogger.log(logging.INFO, "Parsed item id [" + str(item_id) + "] from link [" + str(item) + "]")
            return int(item_id)
        except Exception as e:
            self.jama_config.successLogger.log(logging.INFO, "Unable to extract item ID from reference [" + str(item) + "] -- SKIPPING")



    def create_relationship_post_payload(self, itemID, upstreamRelatedID):
        relationship = {}
        relationship.__setitem__("fromItem", upstreamRelatedID)
        relationship.__setitem__("toItem", itemID)
        relationship.__setitem__("relationshipType", self.jama_config.relationshipTypeID)
        return relationship
