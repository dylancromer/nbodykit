#!/bin/bash

# parse options
while getopts ":h" opt; do
  case ${opt} in
    h )
      echo "usage:"
      echo "    build.sh -h                      Display this help message."
      echo "    build.sh all <version>           Build both the source and the dependencies."
      echo "    build.sh source <version>        Build only the source."
      echo "    build.sh deps                    Build only the dependencies."
      exit 0
      ;;
   \? )
     echo "invalid option: -$OPTARG" 1>&2
     exit 1
     ;;
  esac
done
shift $((OPTIND -1))

subcommand=$1; shift  # Remove build.sh from the argument list
if [[ "$subcommand" != "deps" && $# != 1 ]]
then
    echo "please provide a <version> to build as the 2nd argument"
    exit 1
fi

version=$1; shift
mkdir -p ${NERSC_HOST}

# activate python-mpi-bcast
source /usr/common/contrib/bccp/python-mpi-bcast/activate.sh

case "$subcommand" in

  all )
    MPICC=cc bundle-pip ${NERSC_HOST}/nbodykit-dep.tar.gz -r ../requirements.txt
    bundle-pip ${NERSC_HOST}/nbodykit-${version}.tar.gz ..
  ;;
  source )
    bundle-pip ${NERSC_HOST}/nbodykit-${version}.tar.gz ..
    ;;
  deps )
    MPICC=cc bundle-pip ${NERSC_HOST}/nbodykit-dep.tar.gz -r ../requirements.txt
    ;;
   * )
    echo "invalid build choice -- choose from 'source' or 'deps'"
    exit 1
esac


