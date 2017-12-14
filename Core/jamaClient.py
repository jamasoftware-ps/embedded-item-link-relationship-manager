import time
import requests
import json
import warnings
from requests import HTTPError
import logging
from datetime import datetime

class JamaClient:
    def __init__(self):
        self.config = None
        self.id_map = {}
        self.delete_list = []
        self.auth = None
        self.verify = None
        self.seconds = 2
        self.accessToken = ""
        self.access_time = None
        self.token_expiration = None


    def post_relationship(self, relationshipJSON):
        headers = {
            "Authorization": "Bearer " + self.accessToken,
            "content-type": "application/json"
        }
        url = self.config.restURL + "relationships"
        try:
            response = requests.post(url, data=json.dumps(relationshipJSON), verify=self.verify, headers=headers)
            responseJson = json.loads(response.content)
            if response.status_code == 201:
                return responseJson["meta"]["id"]
            elif response.content.__contains__("already exists"):  ## should never reach here since only processing things that need POST or DELETE
                return None
            else:
                return responseJson["meta"]["message"]
                # self.config.failureLogger.log(logging.ERROR, "Unable to post relationship due to [" + response.content)
                # return None

        except HTTPError as e:
            self.config.failureLogger.log(logging.ERROR, "Unable to connect to Jama server due to [" + e.message + "]")
            return None


    def delete_relationship(self, relationshipID):
        header = {"Authorization": "Bearer " + self.accessToken}
        url = self.config.restURL + "relationships/" + str(relationshipID)
        try:
            response = requests.delete(url, verify=self.verify, headers=header)
            if response.status_code == 204:
                return None
            else:
                self.config.failureLogger.log(logging.ERROR, "Unable to delete relationship [" + str(relationshipID) + "] due to [" + response.content + "]")
                return "FAIL"

        except HTTPError as e:
            self.config.failureLogger.log(logging.ERROR, "Unable to connect to Jama server due to [" + e.message + "]")
            return "FAIL"



    def post_for_access_token(self):
        data = "grant_type=client_credentials"
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        url = self.config.tokenURL
        try:
            response = requests.post(url, data=data, auth=self.auth, verify=self.verify, headers=headers)
            if response.status_code == 200:
                responseJson = json.loads(response.content)
                self.token_expiration = responseJson["expires_in"]
                self.accessToken = responseJson["access_token"]
            else:
                self.config.failureLogger.log(logging.ERROR, "Unable to retrieve updated Jama OAuth token from server. ABORTING")
                exit(1)

        except HTTPError as e:
            self.config.failureLogger.log(logging.ERROR, "Unable to retrieve updated Jama OAuth token from server. ABORTING")
            exit(1)



    def updateAccessToken(self):
        secondsFromStart = None
        if self.access_time is not None:
            secondsFromStart = (datetime.now() - self.access_time).total_seconds()
        if (self.token_expiration is None or self.token_expiration <= 60) or (secondsFromStart is not None and (self.token_expiration - secondsFromStart) <= 60):
            self.post_for_access_token()
            self.access_time = datetime.now()



    def get(self, url):
        self.updateAccessToken()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            header = {"Authorization": "Bearer " + self.accessToken}
            return requests.get(url, verify=self.verify, headers=header)



    def get_all_items(self, projectId):
        items = self.get_all("items?project=" + str(projectId))
        return items



    def get_upstream_related(self, itemId):
        upstream_related = self.get_all("items/" + str(itemId) + "/upstreamrelationships")
        return upstream_related


    def get_all(self, resource):
        all_results = []
        results_remaining = True
        current_start_index = 0
        delim = '&' if '?' in resource else '?'
        while results_remaining:
            start_at = delim + "startAt={}".format(current_start_index)
            url = self.config.restURL + resource + start_at
            # print url
            response = self.get(url)
            json_response = json.loads(response.text)
            if "pageInfo" not in json_response["meta"]:
                # print json_response
                return [json_response["data"]]
            result_count = json_response["meta"]["pageInfo"]["resultCount"]
            total_results = json_response["meta"]["pageInfo"]["totalResults"]
            results_remaining = current_start_index + result_count != total_results
            current_start_index += 20
            all_results.extend(json_response["data"])

        return all_results


    def delay(self):
        time.sleep(self.seconds)

    def setConfig(self, jama_config):
        self.config = jama_config
        self.auth = self.config.auth
        self.verify = self.config.verify_ssl

