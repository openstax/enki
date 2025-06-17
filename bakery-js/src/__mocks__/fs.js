/* eslint-disable no-undef */

const _fs = jest.requireActual('fs')

// const defaultThrow = () => {
//   throw new Error('Not Implemented')
// }

// const newMock = () =>
//   new Proxy(jest.fn(defaultThrow), {
//     get(target, p) {
//       switch (p) {
//         case 'mockRestore':
//           return () => {
//             target.mockRestore()
//             // target.mockImplementation(defaultThrow)
//           }
//       }
//       return Reflect.get(target, p)
//     },
//   })

// const constantsGetter = newMock()
// const constants = new Proxy(
//   {},
//   {
//     get: (_, p) => {
//       const result = constantsGetter(p)
//       if (!result) {
//         throw new Error(`Missing constant: ${p}`)
//       }
//       return result
//     },
//   }
// )

module.exports = {
  existsSync: jest.spyOn(_fs, 'existsSync'),
  readFileSync: jest.spyOn(_fs, 'readFileSync'),
  readdirSync: jest.spyOn(_fs, 'readdirSync'),
  writeFileSync: jest.spyOn(_fs, 'writeFileSync'),
  copyFileSync: jest.spyOn(_fs, 'copyFileSync'),
  mkdirSync: jest.spyOn(_fs, 'mkdirSync'),
  rmSync: jest.spyOn(_fs, 'rmSync'),
  createWriteStream: jest.spyOn(_fs, 'createWriteStream'),
  constants: _fs.constants,
  // constantsGetter,
  // constants,
}
