@Library('pipeline-library') _

pipeline {
  agent { label 'docker' }
  stages {
    stage('Publish Release') {
      when { buildingTag() }
      environment {
        TWINE_CREDS = credentials('pypi-openstax-creds')
        TWINE_USERNAME = "${TWINE_CREDS_USR}"
        TWINE_PASSWORD = "${TWINE_CREDS_PSW}"
        release = getVersion()
      }
      steps {
        sh "docker run --rm -e TWINE_USERNAME -e TWINE_PASSWORD -w /src -v ${WORKSPACE}:/src/:rw python3 /bin/bash -c \"pip install -q twine && python2 setup.py bdist_wheel && twine upload dist/*\""
      }
    }
  }
}
