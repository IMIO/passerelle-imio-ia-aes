pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                fpm -n passerelle-imio-ia-aes -s python -t deb -v 0.1 -d "passerelle" setup.py
            }
        }
        stage('Deploy') {
            steps {
                echo 'Deploying....'
            }
        }
    }
}
