#!/usr/bin/env bash
set -e

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
staging_fe_tag=$(docker service ls | awk '{ if ($2 == "corgi_stag_frontend") { split($5, image, ":"); print image[2] } }')
staging_be_tag=$(docker service ls | awk '{ if ($2 == "corgi_stag_backend") { split($5, image, ":"); print image[2] } }')

prod_fe_tag=$(docker service ls | awk '{ if ($2 == "corgi_prod_frontend") { split($5, image, ":"); print image[2] } }')
prod_be_tag=$(docker service ls | awk '{ if ($2 == "corgi_prod_backend") { split($5, image, ":"); print image[2] } }')

echo "Script dir: ${dir}"
echo "Detected STAGING tags frontend ($staging_fe_tag) and backend ($staging_be_tag)"
echo "Detected PROD tags frontend ($prod_fe_tag) and backend ($prod_be_tag)"

[[ -z "$staging_fe_tag" ]] && echo "Err: Empty tag" && exit 1
[[ -z "$staging_be_tag" ]] && echo "Err: Empty tag" && exit 1
[[ "$staging_fe_tag" = "$staging_be_tag" ]] || (echo "Err: Frontend and backend tags differ" && exit 2)
[[ "$staging_fe_tag" =~ ^[0-9]{8}[.][0-9]{6}$ ]] || (echo "Err: Bad format for tag" && exit 3)

echo -n "Promoting in "
echo -n "5 " && sleep 1
echo -n "4 " && sleep 1
echo -n "3 " && sleep 1
echo -n "2 " && sleep 1
echo -n "1 " && sleep 1
echo

# shellcheck source=SCRIPTDIR/vars.prod.sh
source "${dir}/vars.prod.sh"
export TAG=$staging_fe_tag
# shellcheck source=SCRIPTDIR/deploy.sh
source "${dir}/deploy.sh"
