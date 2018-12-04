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
                VERSION= sh (script: 'echo $(cat version && echo "-" && git log --pretty=format:"%h" -n 1) | tr -d "[:space:]"', returnStdout: true)
            }
            steps {
                sh "fpm -n passerelle-imio-ia-aes -s python -t deb -v `echo ${VERSION}` --prefix /usr -d passerelle setup.py"
            }
        }
        stage('Deploy') {
            steps {
                sh "scp passerelle-imio-ia-aes_`cat version`_all.deb root@puppetmaster.imio.be:/tmp"
            }
        }
    }
}
