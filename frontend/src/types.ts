export type Torrent = {
  name: string
  hash: string
  size: number
  save_path: string
  state: string
  progress: number
  category?: string
  tags?: string
  misplaced: boolean
  suggested_target?: string | null
}

export type TorrentsResp = { items: Torrent[] }