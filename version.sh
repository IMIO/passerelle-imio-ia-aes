version=`echo $(cat version && echo "-" && git log --pretty=format:'%h' -n 1) | tr -d "[:space:]"`
echo $version
