-- desactivate brevo connexion parameters (webhook and API)
DELETE FROM ir_config_parameter
    WHERE key IN ('brevo_webhook_token', 'brevo_api_key');
