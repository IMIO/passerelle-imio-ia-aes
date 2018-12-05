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
                sh "fpm -n passerelle-imio-ia-aes -s python -t deb -v `echo ${VERSION}` --prefix /usr -d passerelle setup.py"
            }
        }
        stage('Deploy') {
            environment {
                VERSION= sh (script: "sh version.sh", returnStdout: true)
            }
            steps {
                withCredentials([usernamePassword(credentialsId: 'nexus-teleservices', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD'), string(credentialsId: 'nexus-url', variable:'NEXUS_URL')]) {
                    sh 'curl -u $USERNAME:$PASSWORD -X POST -H \"Content-Type: multipart/form-data\" --data-binary \"@passerelle-imio-ia-aes_`echo ${VERSION}`_all.deb\" $NEXUS_URL'
                }
            }
        }
    }
}
