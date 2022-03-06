const constructImageSource = ({ registry, name, tag, username, password }) => {
  const source = {}
  if (name == null) { return null }
  if (tag != null) { source.tag = tag }
  if (username != null) { source.username = username }
  if (password != null) { source.password = password }
  if (registry != null) {
    source.repository = `${registry}/${name}`
    source.insecure_registries = [registry]
  } else {
    source.repository = name
  }
  return source
}

module.exports = {
  constructImageSource
}
