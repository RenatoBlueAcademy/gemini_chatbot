import os

from dotenv import load_dotenv


class SecretManager:
    def __init__(self, project, client):
        self.project = project
        self.client = client

    def access_secret_version(self, secret_id, version_id="latest"):
        try:
            name = f"projects/{self.project}/secrets/{secret_id}/versions/{version_id}"
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"Erro ao acessar o Secret Manager: {e}")
            return None

    @staticmethod
    def load_from_env(key):
        load_dotenv()
        return os.getenv(key)
