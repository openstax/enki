import { basename } from "path";

/** If devs run this locally then they may point to an _attic directory of an existing book. */
export const DIRNAMES = {
    IO_RESOURCES: basename(process.env['IO_RESOURCES'] || 'IO_RESOURCES'),
    IO_FETCHED: basename(process.env['IO_FETCHED'] || 'IO_FETCHED'),
    IO_BAKED: basename(process.env['IO_BAKED'] || 'IO_BAKED'),
    IO_DISASSEMBLE_LINKED: basename(process.env['IO_DISASSEMBLE_LINKED'] || 'IO_DISASSEMBLE_LINKED'),
}