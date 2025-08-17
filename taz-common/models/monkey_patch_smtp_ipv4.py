import socket
import smtplib
import logging

from odoo.addons.base.models.ir_mail_server import SMTPConnection, SMTP_TIMEOUT

_logger = logging.getLogger(__name__)


def ipv4_smtp_init(self, server, port, encryption, context=None):
    """Patch du constructeur SMTPConnection pour forcer IPv4"""
    try:
        addr_info = socket.getaddrinfo(server, port, socket.AF_INET, socket.SOCK_STREAM)
        ipv4_addr = addr_info[0][4][0]  # première IPv4
        _logger.debug("Résolution IPv4 réussie pour %s:%s → %s", server, port, ipv4_addr)
    except Exception as e:
        _logger.warning("Impossible de résoudre %s en IPv4, fallback sur hostname. Erreur: %s", server, e)
        ipv4_addr = server

    if encryption == 'ssl':
        self.__obj__ = smtplib.SMTP_SSL(ipv4_addr, port, timeout=SMTP_TIMEOUT, context=context)
    else:
        self.__obj__ = smtplib.SMTP(ipv4_addr, port, timeout=SMTP_TIMEOUT)


SMTPConnection.__init__ = ipv4_smtp_init

_logger.info("Monkey-patch SMTPConnection pour forcer IPv4 appliqué")

