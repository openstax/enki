// JSFiddle: https://jsfiddle.net/m1yag1/5nwzrhu6/3
const flattenObject = (obj, prefix) => {
  const flattened = {}

  Object.keys(obj).forEach((key) => {
    if (typeof obj[key] === 'object' && obj[key] !== null) {
      if (prefix) {
        const newKey = prefix + '_' + key
        Object.assign(flattened, flattenObject(obj[key], newKey))
      } else {
        Object.assign(flattened, flattenObject(obj[key], key))
      }
    } else if (prefix) {
      flattened[prefix + '_' + key] = obj[key]
    } else {
      flattened[key] = obj[key]
    }
  })

  return flattened
}

export default flattenObject
