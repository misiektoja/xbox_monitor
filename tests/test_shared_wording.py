"""Pins the sentences this tool shares with its sibling monitors.

The list is the intersection of the string literals in spotify_monitor, spotify_profile_monitor,
instagram_monitor, github_monitor, psn_monitor and psn's steam counterpart, taken on 2026-09-03 with the
per-function diff from playbook section 15.9. The sibling sources are not available here, so the contract is
asserted against this tool's own source: changing one of these sentences means changing it in every sibling too.
"""

import ast

import pytest

import xbox_monitor as monitor


# Collects this tool's string literals as templates, with every interpolated expression collapsed to a placeholder
def source_templates():
    tree = ast.parse(monitor.Path(monitor.__file__).read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.add(" ".join(node.value.split()))
        elif isinstance(node, ast.JoinedStr):
            found.add(" ".join("".join(part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else "{}" for part in node.values).split()))
    return found


TEMPLATES = source_templates()

SHARED_WORDING = (
    '(or just answer Y below)',
    '* Cannot clear the screen contents',
    '* Email sent successfully !',
    '* Sending test email notification ...',
    '* Signal {} received',
    '* The password is checked by signing in to {} as {}. Nothing is sent',
    '* You pressed Ctrl+C, tool is terminated.',
    '/configuration/#configuration-file',
    '/configuration/#smtp-settings',
    '/configuration/#tls-verification',
    '/troubleshooting/#doctor-preflight',
    'ASCII log separators',
    "ASCII_LOG_SEPARATORS must be 'Auto', 'On' or 'Off'",
    'After Doctor passes, start monitoring:',
    'Alerts: {}. No email was sent during this passive check',
    'All checks passed. You are good to go!',
    'All critical checks passed with {} warning(s). Review the warnings above.',
    'Check setup before monitoring:',
    'Check the setup before relying on it',
    'Checking the sign-in with the mail server ...',
    'Config written to: {}',
    'Configuration & dotenv files',
    'Configuration applied',
    'Configuration file loaded',
    'Configure email notifications?',
    'Continue without the {}? {}',
    "Could not create a unique backup for '",
    "Could not find executable '{}'",
    "Could not initialize CSV file '{}': {}",
    'Detected install method: {}',
    'Disable coloured output in the terminal',
    'Discard all entered answers and exit?',
    'Discard answers and exit',
    'Doctor will not write files. Each approved test sends one real message.',
    'Easiest start (guided setup wizard):',
    'Edit one section without losing the other answers.',
    'Email notifications stay off until every mail server setting is answered.',
    'Email notifications stay off until the mail server accepts the settings.',
    'Enable TLS/SSL for SMTP?',
    'Enter a number between 1 and {}.',
    'Enter a positive duration such as 120, 2m, 1.5h, 1h 30m or 1d.',
    'Enter the SMTP password (input hidden):',
    'Every outbound request checks the server certificate',
    "Failed to write to CSV file '{}': {}",
    'Information and diagnostics',
    'Leave the destination files unchanged.',
    'Liveness check, timestamp:',
    'Max characters per screen line (not log), use 999 to auto-detect terminal width, ignored if -d is set',
    'Monitoring healthy for',
    'No configuration file selected',
    'No dotenv file selected',
    'Notifications (email)',
    'Off, server certificates are not checked',
    'Optional CSV output path (blank disables it)',
    'Optional delivery tests',
    'Output logging is disabled',
    "Please answer 'y' or 'n'.",
    'Press Enter to accept the shown default. Ctrl+C cancels.',
    'Python {} is supported',
    'Python {} is unsupported',
    'Required dependency {} is installed',
    'Required dependency {} is missing',
    'Review or change settings',
    'Run doctor now? It writes no files and offers real delivery tests only with separate approval.',
    'Run the guided setup wizard now?',
    'SMTP connection and login succeeded',
    'Secrets from command line',
    'Secrets from config file',
    'Secrets from environment',
    'Secrets go to the dotenv file. Non-secret settings go to the config file.',
    'Send one test email now? This will deliver a real message',
    'Send test email to verify SMTP settings',
    'Set VERIFY_SSL back to True unless this network intercepts TLS with its own certificate authority',
    'Setup answers retained.',
    'Setup cancelled. Destination files were not changed.',
    'Setup is saved. Start monitoring with the command above when ready.',
    'Setup is saved. Use the commands below when ready.',
    'Start monitoring now? Monitoring will continue until Ctrl+C.',
    'TLS certificate verification is off',
    'TLS certificate verification is on',
    'Terminal only (logging disabled)',
    'The detected terminal screen width is: {} characters',
    'The mail server accepted the sign-in. No email was sent.',
    'The settings were kept without being checked. Run --doctor to check the sign-in again.',
    'The setup wizard needs an interactive terminal (TTY).',
    'This asks a few questions and writes a ready-to-run configuration.',
    'This is test email - your SMTP settings seems to be correct !',
    'Trace what the tool is doing',
    'Try entering the {} again?',
    'VERIFY_SSL is False, so an intercepted connection cannot be told apart from the real service',
    'What would you like to do?',
    'Which email notifications should be enabled?',
    'Which setup section should be changed?',
    'Write the displayed settings to the selected files.',
    'Write the normal per-target log file?',
    'mail server settings',
    'use --verbose or --debug',
    '{} --send-test-email',
    '{} check(s) failed, {} warning(s). Fix the failures above before relying on the tool.',
)


@pytest.mark.parametrize("sentence", SHARED_WORDING)
# Wording shared with the siblings has to stay identical, or the next edit silently forks the contract
def test_the_shared_wording_is_unchanged(sentence):
    assert sentence in TEMPLATES
