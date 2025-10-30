import logging
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
import smtplib


logger = logging.getLogger(__name__)


class DebugSMTPEmailBackend(EmailBackend):
    """SMTP backend that enables smtplib debug output when SMTP_DEBUG=True.

    Use by setting EMAIL_BACKEND="core.email_backends.DebugSMTPEmailBackend".
    """

    def open(self):
        """Open a network connection and optionally log in.

        Same behavior as Django's SMTP EmailBackend but enables protocol debug
        before AUTH so the login exchange is visible in logs when SMTP_DEBUG=True.
        """
        if self.connection:  # Already open
            return False

        try:
            if self.use_ssl:
                self.connection = smtplib.SMTP_SSL(self.host, self.port or 0, timeout=self.timeout)
            else:
                self.connection = smtplib.SMTP(self.host, self.port or 0, timeout=self.timeout)

            if getattr(settings, "SMTP_DEBUG", False):
                try:
                    self.connection.set_debuglevel(1)
                except Exception:
                    logger.debug("Could not set SMTP debuglevel", exc_info=True)

            # Identify ourselves to SMTP server.
            self.connection.ehlo()
            if not self.use_ssl and self.use_tls:
                self.connection.starttls()
                # Re-identify ourselves over TLS connection.
                self.connection.ehlo()

            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if self.connection is not None:
                try:
                    self.connection.close()
                except Exception:
                    pass
                finally:
                    self.connection = None
            raise
