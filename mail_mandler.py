import dtlpy as dl
import logging

logger = logging.getLogger(__name__)


class MailHandler(dl.BaseServiceRunner):
    def __init__(self, service_name: str):
        self.service_name = service_name

    def send_mail(self, email: str, item: dl.Item, msg: str):
        try:
            dl.projects._send_mail(
                project_id=None,
                send_to=email,
                title='{} fail in project id :  {}'.format(self.service_name, item.project.id),
                content='item: {} \n dataset: {} \n url: {} \n msg:{}'.format(
                    item.id,
                    item.dataset.id,
                    item.platform_url,
                    msg
                )
            )
        except Exception:
            logger.exception('Failed to send mail to {}'.format(email))

    def send_alert(self, item: dl.Item, msg):
        try:
            item.metadata['system']['{}_fail'.format(self.service_name)] = msg
            item.update(system_metadata=True)
            for email in [
                item.creator
            ]:
                self.send_mail(email=email, item=item, msg=msg)
        except:
            logger.exception('Failed to send mail')
