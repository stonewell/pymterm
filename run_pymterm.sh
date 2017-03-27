#/bin/bash
READLINK_OPT=

case "${host}" in
  *Linux* )
  READLINK_OPT="-f"
  ;;
  *)
esac

SCRIPT_PATH="${BASH_SOURCE[0]}";
if([ -h "${SCRIPT_PATH}" ]) then
  while([ -h "${SCRIPT_PATH}" ]) do SCRIPT_PATH=`readlink ${READLINK_OPT} "${SCRIPT_PATH}"`; done
fi
pushd . > /dev/null
cd `dirname ${SCRIPT_PATH}` > /dev/null
SCRIPT_PATH=`pwd`;
popd  > /dev/null

. ${SCRIPT_PATH}/venv/bin/activate
python ${SCRIPT_PATH}/pymterm/pymterm.py --session_type pty -l ${SCRIPT_PATH}/run_pymterm.log

deactivate
