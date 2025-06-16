/* eslint-disable no-undef */

const defaultThrow = () => {
  throw new Error('Not Implemented')
}

const newMock = () =>
  new Proxy(jest.fn(defaultThrow), {
    get(target, p) {
      switch (p) {
        case 'mockRestore':
          return () => {
            target.mockRestore()
            target.mockImplementation(defaultThrow)
          }
      }
      return Reflect.get(target, p)
    },
  })

const constantsGetter = newMock()
const constants = new Proxy(
  {},
  {
    get: (_, p) => {
      const result = constantsGetter(p)
      if (!result) {
        throw new Error(`Missing constant: ${p}`)
      }
      return result
    },
  }
)

module.exports = {
  existsSync: newMock(),
  readFileSync: newMock(),
  readdirSync: newMock(),
  writeFileSync: newMock(),
  copyFileSync: newMock(),
  mkdirSync: newMock(),
  rmSync: newMock(),
  createWriteStream: newMock(),
  constantsGetter,
  constants,
}
