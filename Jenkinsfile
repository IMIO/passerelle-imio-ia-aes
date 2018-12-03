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
            steps {
                sh "fpm -n passerelle-imio-ia-aes -s python -t deb -v `cat version``echo "-"``git log --pretty=format:'%h' -n 1` -d passerelle setup.py"
            }
        }
        stage('Deploy') {
            steps {
                echo 'Deploying....'
            }
        }
    }
}
