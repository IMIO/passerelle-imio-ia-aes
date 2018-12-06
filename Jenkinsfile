pipeline {
    agent any
    triggers {
        pollSCM('*/3 * * * *')
    }
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
                sh "fpm -a amd64 -n passerelle-imio-ia-aes -s python -t deb -v `echo ${VERSION}` --prefix /usr -d passerelle setup.py"
                withCredentials([string(credentialsId: 'gpg-passphrase-system@imio.be', variable:'PASSPHRASE')]){
                    sh ('''dpkg-sig --gpg-options "--yes --batch --passphrase '$PASSPHRASE' " -s builder -k 9D4C79E197D914CF60C05332C0025EEBC59B875B passerelle-imio-ia-aes_`echo ${VERSION}`_amd64.deb''')
                }
            }
        }
        stage('Deploy') {
            environment {
                VERSION= sh (script: "sh version.sh", returnStdout: true)
            }
            steps {
                withCredentials([usernameColonPassword(credentialsId: 'nexus-teleservices', variable: 'CREDENTIALS'),string(credentialsId: 'nexus-url', variable:'NEXUS_URL')]) {
                    sh ('curl -v --fail -u $CREDENTIALS -X POST -H Content-Type:multipart/form-data --data-binary @passerelle-imio-ia-aes_`echo ${VERSION}`_amd64.deb $NEXUS_URL')
                }
            }
        }
    }
}

