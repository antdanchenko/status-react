import base64
import requests
import time
from datetime import datetime
import testdroid


class BitBar:

    class ResponseError(Exception):

        def __init__(self, msg, status_code):
            super(Exception, self).__init__("Request Error: code %s: %s" %
                                            (status_code, msg))
            self.status_code = status_code

    class NameNotFoundException(Exception):
        def __init__(self, name):
            super(Exception, self).__init__("Name: '%s' is not found on BitBar" % name)

    def __init__(self, api_key):
        self.api_key = base64.b64encode(api_key.encode('utf-8') + ':'.encode('utf-8')).decode('utf-8')
        self.url = 'https://cloud.testdroid.com/api/v2/me'
        self.headers = {"Accept": "application/json", 'Authorization': 'Basic %s' % self.api_key}

    def get(self, url):
        response = requests.get(url, headers=self.headers)
        if response.status_code not in range(200, 300):
            raise self.ResponseError(response.text, response.status_code)
        return response.json()

    def create_project(self, project_name):
        response = requests.post(url=self.url + '/projects',
                                 data={"name": project_name},
                                 headers=self.headers)
        return response.text

    def get_projects(self):
        return self.get(self.url + '/projects')

    def get_test_runs(self, project_id):
        return self.get(self.url + '/projects/' + str(project_id) + '/runs')

    def get_device_runs(self, project_id, test_run_id):
        return self.get(self.url + '/projects/' + str(project_id) + '/runs/' + str(test_run_id) + '/device-runs')

    def get_performance(self, project_id, test_run_id, device_run_id):
        return self.get(self.url + '/projects/' + str(project_id) + '/runs/' + str(test_run_id) + '/device-runs/'
                        + str(device_run_id) + '/performance')

    def get_project_id_by(self, project_name):
        all_projects = self.get_projects()
        for i in all_projects['data']:
            if i['name'] == project_name:
                project = i
                break
        else:
            raise BaseException('Project is not found by given name')
        return project['id']

    def get_test_run_id_by(self, project_id, test_run_name):
        all_test_runs = self.get_test_runs(project_id)
        for i in all_test_runs['data']:
            if i['displayName'] == test_run_name:
                test_run = i
                break
        else:
            raise self.NameNotFoundException(test_run_name)
        return test_run['id']

    def get_performance_by(self, project_name, test_run_name):
        project_id = self.get_project_id_by(project_name)
        test_id = self.get_test_run_id_by(project_id, test_run_name)
        all_device_runs = self.get_device_runs(project_id, test_id)
        device_run = all_device_runs['data'][0]['id']
        return self.get_performance(project_id, test_id, device_run)

    def get_previous_project_name(self):
        sorted_projects = sorted(self.get_projects()['data'], key=lambda k: k['createTime'], reverse=True)
        return sorted_projects[1]['name']
