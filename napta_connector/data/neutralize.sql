-- desactivate napta connexion parameters
DELETE FROM ir_config_parameter
    WHERE key IN ('napta_client_id', 'napta_client_secret');
