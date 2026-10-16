#!/bin/sh
# Read-only ALSA sequencer kernel diagnostic. No sudo, no modprobe.
set -eu
printf 'ALSA_KERNEL_RELEASE: '
uname -r
if [ -c /dev/snd/seq ]; then
    echo 'ALSA_SEQ_NODE: character device present'
elif [ -e /dev/snd/seq ]; then
    echo 'ALSA_SEQ_NODE: path exists but is not a character device'
else
    echo 'ALSA_SEQ_NODE: absent'
fi

config_file="/boot/config-$(uname -r)"
if [ -r /proc/config.gz ] && command -v gzip >/dev/null 2>&1; then
    echo 'ALSA_KERNEL_CONFIG_SOURCE: /proc/config.gz'
    gzip -dc /proc/config.gz | grep -E '^(CONFIG_SOUND|CONFIG_SND|CONFIG_SND_SEQUENCER)=' || true
    gzip -dc /proc/config.gz | grep -E '^# CONFIG_SND_SEQUENCER is not set' || true
elif [ -r "$config_file" ]; then
    echo "ALSA_KERNEL_CONFIG_SOURCE: $config_file"
    grep -E '^(CONFIG_SOUND|CONFIG_SND|CONFIG_SND_SEQUENCER)=|^# CONFIG_SND_SEQUENCER is not set' "$config_file" || true
else
    echo 'ALSA_KERNEL_CONFIG_SOURCE: unavailable (cannot infer build-time support)'
fi

if [ -r /proc/asound/seq/clients ]; then
    echo 'ALSA_PROC_SEQUENCER: available'
else
    echo 'ALSA_PROC_SEQUENCER: unavailable'
fi
if [ -r /proc/modules ]; then
    echo 'ALSA_LOADED_SEQ_MODULES:'
    grep -E '^snd_seq([_[:space:]]|$)' /proc/modules || echo '(none listed; support may be built into kernel)'
fi
module_tree="/lib/modules/$(uname -r)"
if [ -d "$module_tree" ]; then
    echo 'ALSA_MODULE_TREE: present'
else
    echo 'ALSA_MODULE_TREE: absent (cannot infer kernel support)'
fi
