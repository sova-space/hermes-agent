#!/bin/sh
# pre_gateway_dispatch hook — silence hermes for commands addressed to @sova_finance_bot.
# The finance bot handles those directly; hermes should stay completely silent.
#
# Hermes passes the event payload as JSON on stdin. The MessageEvent is
# stringified inside the "extra" field, so @sova_finance_bot appears in the
# raw JSON if the message was directed at the finance bot.
input=$(cat)
if echo "$input" | grep -q "@sova_finance_bot"; then
    printf '{"action":"skip","reason":"command addressed to sova_finance_bot"}'
fi
