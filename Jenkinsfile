pipeline {
    agent any
    options {
        // Keep the 50 most recent builds
        buildDiscarder(logRotator(numToKeepStr:'50'))
    }
    stages {
        stage('Build') {
            environment {
                VERSION= sh (script: "sh version.sh", returnStdout: true)
            }
            steps {
                sh "fpm -a amd64 \
                --python-bin python3 \
                --python-pip pip3 \
                --python-package-name-prefix python3 \
                -n passerelle-imio-ia-aes \
                -s python \
                -t deb \
                -v `echo ${VERSION}` \
                --python-install-lib /usr/lib/python3/dist-packages \
                --no-auto-depends \
                -d passerelle \
                setup.py"
                withCredentials([string(credentialsId: 'gpg-passphrase-system@imio.be', variable:'PASSPHRASE')]){
                    sh ('''dpkg-sig --gpg-options "--yes --batch --passphrase '$PASSPHRASE' " -s builder -k 9D4C79E197D914CF60C05332C0025EEBC59B875B passerelle-imio-ia-aes_`echo ${VERSION}`_amd64.deb''')
                }
            }
        }
        stage('Push deb to buster apt repo') {
            when {
                branch 'master'
            }
            environment {
                VERSION= sh (script: "sh version.sh", returnStdout: true)
            }
            steps {
                withCredentials([usernameColonPassword(credentialsId: 'nexus-teleservices', variable: 'CREDENTIALS'),string(credentialsId: 'nexus-url-buster', variable:'NEXUS_URL_BUSTER')]) {
                    sh ('curl -v --fail -u $CREDENTIALS -X POST -H Content-Type:multipart/form-data --data-binary @passerelle-imio-ia-aes_`echo ${VERSION}`_amd64.deb $NEXUS_URL_BUSTER')
                }
            }
        }
        stage('Push deb to buster-test apt repo') {
            when {
                not {
                    branch 'master'
                }
            }
            environment {
                VERSION= sh (script: "sh version.sh", returnStdout: true)
            }
            steps {
                withCredentials([usernameColonPassword(credentialsId: 'nexus-teleservices', variable: 'CREDENTIALS'),string(credentialsId: 'nexus-url-buster-test', variable:'NEXUS_URL_BUSTER')]) {
                    sh ('curl -v --fail -u $CREDENTIALS -X POST -H Content-Type:multipart/form-data --data-binary @passerelle-imio-ia-aes_`echo ${VERSION}`_amd64.deb $NEXUS_URL_BUSTER')
                }
            }
        }
    }
    post {
        always {
            sh "rm -f passerelle-imio-ia-aes_*.deb"
        }
        success {
            cleanWs()
        }
    }
}

