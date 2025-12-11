function pad2(n: number) {
  return n.toString().padStart(2, "0");
}

/**
 * 将 ISO 时间字符串格式化为 "YYYY-MM-DD HH:mm:ss"
 */
export function formatDateTime(value: string) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const year = d.getFullYear();
  const month = pad2(d.getMonth() + 1);
  const day = pad2(d.getDate());
  const hour = pad2(d.getHours());
  const minute = pad2(d.getMinutes());
  const second = pad2(d.getSeconds());
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
}

