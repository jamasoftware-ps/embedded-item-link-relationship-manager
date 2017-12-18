import logging
import ConfigParser
import os
from datetime import datetime
from dateutil import parser


class Config:
    def __init__(self):
        self.logger_directory = self.setup_logger_directory()
        self.successLoggerFile = os.path.join(self.logger_directory, 'updates.log')
        self.failureLoggerFile = os.path.join(self.logger_directory, 'errors.log')
        self.successLogger = self.setup_logger("success_logger", self.successLoggerFile, level=logging.INFO)
        self.failureLogger = self.setup_logger("failure_logger", self.failureLoggerFile, level=logging.ERROR)

        self.clientID = ""
        self.clientSecret = ""
        self.baseURL = ""
        self.testCaseStepItemTypeID = None
        self.relationshipTypeID = None
        self.testCaseField = ""
        self.projectID = None

        self.credentialFile = "credentials.cfg"
        self.config = ConfigParser.RawConfigParser()
        self.load()

        if self.baseURL.startswith("https://") == False:
            self.baseURL = "https://" + self.baseURL
        self.restURL = self.baseURL + "/rest/v1/"
        self.linkURL = self.baseURL + "/perspective.req?"
        self.tokenURL = self.baseURL + "/rest/oauth/token"
        self.auth = (self.clientID, self.clientSecret)
        self.verify_ssl = True

        self.last_run_time_file = "last_run.cfg"
        self.last_run_time = self.load_last_run_time()
        if self.last_run_time is not None:
            self.last_run_time = parser.parse(self.last_run_time)

    def load(self):
        try:
            config = ConfigParser.RawConfigParser()
            config.read(self.credentialFile)
            self.baseURL = config.get("CREDENTIALS", "baseURL")
            self.clientID = config.get("CREDENTIALS", "clientID")
            self.clientSecret = config.get("CREDENTIALS", "clientSecret")
            self.relationshipTypeID = config.get("CREDENTIALS", "relationshipTypeID")
            self.testCaseStepItemTypeID = config.get("CREDENTIALS", "itemTypeID")
            self.testCaseField = config.get("CREDENTIALS", "testCaseField")
            if self.testCaseField != "description":
                self.testCaseField = self.testCaseField + "$"
            try:
                self.projectID = config.get("CREDENTIALS", "projectID")
            except Exception as e:
                self.projectID = None

        except Exception as e:
            print 'Unable to open or read credentials file due to [' + str(e.message) + ']'
            print 'Create a file named "credentials.properties" that contains the following parameters:'
            print 'baseURL:https://{base_url}'
            print 'clientID:your_client_ID'
            print 'clientSecret:your_client_Secret'
            print 'itemTypeID:test_case_step_itemType_ID'
            print 'relationshipID:relationship_type_ID'
            print 'projectID:projectID (optional)'

    def setup_logger(self, name, log_file, level):
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        """Function setup as many loggers as you want"""

        handler = logging.FileHandler(log_file)
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)

        return logger

    def setup_logger_directory(self):
        main_directory = "logs"
        if not os.path.exists(main_directory):
            os.makedirs(main_directory)

        directory = os.path.join(main_directory, str(parser.parse(datetime.now().isoformat())).replace(":", "-"))
        if not os.path.exists(directory):
            os.makedirs(directory)
            return directory

    def load_last_run_time(self):
        try:
            config = ConfigParser.RawConfigParser()
            config.read(self.last_run_time_file)
            last_run = config.get("TIME", "lastRun")
            self.successLogger.log(logging.INFO,
                                   "Successfully extracted last run time from lastRun.cfg Last run time was [" + last_run + "]")
            return last_run
        except Exception as e:
            self.successLogger.log(logging.INFO, "Could not extract last run time from lastRun.cfg due to [" + str(
                e.message) + "]. All items will be processed during this run.")
            return None

    def update_last_run_time(self):
        try:
            config = ConfigParser.RawConfigParser()
            config.add_section("TIME")
            datetimestring = str(self.get_now())
            config.set("TIME", "lastRun", datetimestring)
            with open(self.last_run_time_file, 'w') as f:
                config.write(f)
                self.successLogger.log(logging.INFO,
                                       "Successfully created lastRun.cfg and recorded lastest run as: [" + datetimestring + "]")
        except Exception as e:
            self.failureLogger.log(logging.ERROR,
                                   "Unable to create lastRun.cfg to record latest run date/time. All items will be processed during next run.")


    def get_now(self):
        # import pytz
        # datetime.utcnow().replace(tzinfo=pytz.utc)
        return datetime.utcnow().isoformat()
        # return datetime.utcnow()
