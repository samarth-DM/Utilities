try:
    import logging
    import boto3
    from botocore.exceptions import ClientError
    import os
    import sys
    import threading
    import math
    import re
    from boto3.s3.transfer import TransferConfig
except Exception as e:
    pass

ACCESS_KEY = ""
SECRET_KEY = ""
REGION_NAME= ""
BucketName = ""
KEY = ""


class Size:
    @staticmethod
    def convert_size(size_bytes):

        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return "%s %s" % (s, size_name[i])

class ProgressPercentage(object):
    def __init__(self, filename, filesize):
        self._filename = filename
        self._size = filesize
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        def convertSize(size):
            if (size == 0):
                return '0B'
            size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
            i = int(math.floor(math.log(size,1024)))
            p = math.pow(1024,i)
            s = round(size/p,2)
            return '%.2f %s' % (s,size_name[i])

        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)        " % (
                    self._filename, convertSize(self._seen_so_far), convertSize(self._size),
                    percentage))
            sys.stdout.flush()

class AWSS3(object):

    """Helper class to which add functionality on top of boto3 """

    def __init__(self, bucket, aws_access_key_id, aws_secret_access_key, region_name):

        self.BucketName = bucket
        self.client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )

    def get_size_of_files(self, Key):
        response = self.client.head_object(Bucket=self.BucketName, Key=Key)
        size = response["ContentLength"]
        return {"bytes": size, "size": Size.convert_size(size)}

    def put_files(self, Response=None, Key=None):
        """
        Put the File on S3
        :return: Bool
        """
        try:

            response = self.client.put_object(
                ACL="private", Body=Response, Bucket=self.BucketName, Key=Key
            )
            return "ok"
        except Exception as e:
            print("Error : {} ".format(e))
            return "error"

    def item_exists(self, Key):
        """Given key check if the items exists on AWS S3 """
        try:
            response_new = self.client.get_object(Bucket=self.BucketName, Key=str(Key))
            return True
        except Exception as e:
            return False

    def get_item(self, Key):

        """Gets the Bytes Data from AWS S3 """

        try:
            response_new = self.client.get_object(Bucket=self.BucketName, Key=str(Key))
            return response_new["Body"].read()

        except Exception as e:
            print("Error :{}".format(e))
            return False

    def find_one_update(self, data=None, key=None):

        """
        This checks if Key is on S3 if it is return the data from s3
        else store on s3 and return it
        """

        flag = self.item_exists(Key=key)

        if flag:
            data = self.get_item(Key=key)
            return data

        else:
            self.put_files(Key=key, Response=data)
            return data

    def delete_object(self, Key):

        response = self.client.delete_object(Bucket=self.BucketName, Key=Key,)
        return response

    def get_all_keys(self, Prefix=""):

        """
        :param Prefix: Prefix string
        :return: Keys List
        """
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.BucketName, Prefix=Prefix)

            tmp = []

            for page in pages:
                for obj in page["Contents"]:
                    tmp.append(obj["Key"])

            return tmp
        except Exception as e:
            return []

    def print_tree(self):
        keys = self.get_all_keys()
        for key in keys:
            print(key)
        return None

    def find_one_similar_key(self, searchTerm=""):
        keys = self.get_all_keys()
        return [key for key in keys if re.search(searchTerm, key)]

    def __repr__(self):
        return "AWS S3 Helper class "

    def download_file(self,file_name, object_name):

        try:
            response = self.client.download_file(
                Bucket=self.BucketName,
                Key=object_name,
                Filename=file_name,
                Config=TransferConfig(
                    max_concurrency=10,
                    use_threads=True
                ),
                Callback=ProgressPercentage(file_name,
                                            (self.client.head_object(Bucket=self.BucketName,
                                                                     Key=object_name))["ContentLength"])
            )
        except ClientError as e:
            logging.error(e)
            return False
        return True



helper = AWSS3(aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, bucket=BucketName, region_name='us-east-1')
helper.download_file(file_name='test.zip', object_name=KEY)
