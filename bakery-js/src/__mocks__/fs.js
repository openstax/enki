/* eslint-disable no-undef */

const _fs = jest.requireActual('fs')

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
}
