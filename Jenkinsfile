pipeline {
    agent any

    triggers {
        githubPush()
    }

    environment {
        DOCKER_USER = 'usmanfarooq317'
        IMAGE_NAME = 'usman-apis-dashboard'   // new image name
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/usmanfarooq317/usman-apis-5090.git'
            }
        }

        stage('Generate Version Tag') {
            steps {
                script {
                    // fetch existing tags from Docker Hub (requires jq installed on Jenkins agent)
                    def existingTags = sh(
                        script: "curl -s https://hub.docker.com/v2/repositories/${DOCKER_USER}/${IMAGE_NAME}/tags/?page_size=100 | jq -r '.results[].name' | grep -E '^v[0-9]+' || true",
                        returnStdout: true
                    ).trim()

                    if (!existingTags) {
                        env.NEW_VERSION = "v1"
                    } else {
                        def numbers = existingTags.readLines().collect { it.replace('v', '').toInteger() }
                        env.NEW_VERSION = "v" + (numbers.max() + 1)
                    }
                    echo "✅ New version to build: ${env.NEW_VERSION}"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${DOCKER_USER}/${IMAGE_NAME}:latest ."
            }
        }

        stage('Tag & Push to Docker Hub') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: 'docker-hub', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                        sh """
                            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                            docker tag ${DOCKER_USER}/${IMAGE_NAME}:latest ${DOCKER_USER}/${IMAGE_NAME}:${env.NEW_VERSION}
                            docker push ${DOCKER_USER}/${IMAGE_NAME}:latest
                            docker push ${DOCKER_USER}/${IMAGE_NAME}:${env.NEW_VERSION}
                        """
                    }
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                script {
                    try {
                        // usman-ec2-key is Jenkins SSH credential ID (private key)
                        sshagent(['usman-ec2-key']) {
                            // Replace ubuntu@<EC2_IP> with your actual EC2 host
                            sh """
                                ssh -o StrictHostKeyChecking=no ubuntu@13.50.238.43 '
                                    docker pull ${DOCKER_USER}/${IMAGE_NAME}:${env.NEW_VERSION} &&
                                    docker stop ${IMAGE_NAME} || true &&
                                    docker rm ${IMAGE_NAME} || true &&
                                    docker run -d --name ${IMAGE_NAME} -p 5090:5090 ${DOCKER_USER}/${IMAGE_NAME}:${env.NEW_VERSION}
                                '
                            """
                        }
                    } catch (err) {
                        echo "❌ EC2 Deploy Failed! Reverting Docker Tag..."

                        withCredentials([usernamePassword(credentialsId: 'docker-hub', passwordVariable: 'DOCKER_PASS', usernameVariable: 'DOCKER_USER')]) {
                            sh """
                                curl -X DELETE -u "${DOCKER_USER}:${DOCKER_PASS}" \
                                https://hub.docker.com/v2/repositories/${DOCKER_USER}/${IMAGE_NAME}/tags/${env.NEW_VERSION}/
                            """
                        }

                        sh "docker rmi ${DOCKER_USER}/${IMAGE_NAME}:${env.NEW_VERSION} || true"

                        error("Deployment Failed, tag reverted.")
                    }
                }
            }
        }
    }

    post {
        success {
            echo "✅ Build, Push & Deploy Successful! Version: ${env.NEW_VERSION}"
        }
        failure {
            echo "❌ Pipeline Failed! Docker tag is reverted if created."
        }
    }
}
